"""The two-agent Strands surface used by Live Preflight.

This module intentionally imports Strands lazily. Offline deterministic tests
must remain runnable, while the live command must fail closed if the SDK or AWS
credential chain is unavailable.
"""

from __future__ import annotations

import json
import platform
import threading
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .domain import (
    LaunchTask,
    ProjectInput,
    calculate_readiness,
    default_tasks,
    demo_budget_items,
    demo_project,
)
from .domain import (
    calculate_critical_path as deterministic_critical_path,
)
from .preflight import PreflightConfig
from .service import recompute_rescue_from_snapshots

MAX_AGENT_INPUT_BYTES = 16 * 1024
MAX_MODEL_OUTPUT_TOKENS = 1_024
LIVE_TIMEOUT_SECONDS = 120
BEDROCK_CONNECT_TIMEOUT_SECONDS = 3
BEDROCK_READ_TIMEOUT_SECONDS = 20
MANAGER_MAX_CYCLES = 6
REVIEWER_MAX_CYCLES = 5
RESCUE_MANAGER_MAX_CYCLES = 4
RESCUE_REVIEWER_MAX_CYCLES = 6


class LivePreflightFailed(RuntimeError):
    """Raised when real agent execution does not satisfy the preflight."""


def _safe_exception_type_chain(exc: BaseException) -> str:
    """Expose only exception class names, never provider messages or request data."""

    names: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(names) < 5:
        seen.add(id(current))
        name = type(current).__name__
        if isinstance(current, LivePreflightFailed):
            safe_code = str(current).split(":", 1)[0]
            if safe_code in {
                "MODEL_CYCLE_LIMIT_EXCEEDED",
                "REQUIRED_TOOL_NOT_AVAILABLE",
                "UNEXPECTED_TOOL_FAILURE",
            }:
                name = f"{name}[{safe_code}]"
        names.append(name)
        original = getattr(current, "original_exception", None)
        current = original if isinstance(original, BaseException) else current.__cause__
    return ":".join(names)


@dataclass
class _RequiredToolSequence:
    """Advance a forced-tool sequence only after a successful tool result."""

    required_tools: tuple[str, ...]
    maximum_cycles: int
    index: int = 0
    cycles: int = 0

    def required_for_next_cycle(self) -> str | None:
        self.cycles += 1
        if self.cycles > self.maximum_cycles:
            raise LivePreflightFailed("MODEL_CYCLE_LIMIT_EXCEEDED")
        return self.required_tools[self.index] if self.index < len(self.required_tools) else None

    def mark_success(self, tool_name: str) -> None:
        if self.index < len(self.required_tools) and self.required_tools[self.index] == tool_name:
            self.index += 1

    def mark_failed(self, tool_name: str) -> None:
        if self.index >= len(self.required_tools) or self.required_tools[self.index] != tool_name:
            raise LivePreflightFailed(f"UNEXPECTED_TOOL_FAILURE:{tool_name}")


def _required_tool_model(
    model_class: type[Any],
    config: PreflightConfig,
    required_tools: tuple[str, ...],
    maximum_cycles: int,
) -> Any:
    """Create a Bedrock model that forces one real required tool per model cycle."""

    class RequiredToolModel(model_class):  # type: ignore[misc]
        def __init__(self) -> None:
            import boto3  # type: ignore[import-untyped]
            from botocore.config import Config  # type: ignore[import-untyped]

            super().__init__(
                model_id=config.model_id,
                boto_session=boto3.Session(region_name=config.region),
                max_tokens=MAX_MODEL_OUTPUT_TOKENS,
                boto_client_config=Config(
                    connect_timeout=BEDROCK_CONNECT_TIMEOUT_SECONDS,
                    read_timeout=BEDROCK_READ_TIMEOUT_SECONDS,
                    retries={"total_max_attempts": 1, "mode": "standard"},
                ),
            )
            self.sequence = _RequiredToolSequence(required_tools, maximum_cycles)

        def mark_tool_success(self, tool_name: str) -> None:
            self.sequence.mark_success(tool_name)

        def mark_tool_failed(self, tool_name: str) -> None:
            self.sequence.mark_failed(tool_name)

        async def stream(
            self,
            messages: Any,
            tool_specs: list[dict[str, Any]] | None = None,
            system_prompt: str | None = None,
            *,
            tool_choice: dict[str, Any] | None = None,
            **kwargs: Any,
        ) -> AsyncGenerator[Any, None]:
            required_name = self.sequence.required_for_next_cycle()
            if required_name is not None and tool_specs:
                matching_specs = [spec for spec in tool_specs if spec.get("name") == required_name]
                if matching_specs:
                    tool_specs = matching_specs
                    tool_choice = {"tool": {"name": required_name}}
                else:
                    available = sorted(str(spec.get("name", "")) for spec in tool_specs)
                    raise LivePreflightFailed(
                        "REQUIRED_TOOL_NOT_AVAILABLE:"
                        f"required={required_name};available={','.join(available)}"
                    )
            elif required_name is not None:
                raise LivePreflightFailed(f"REQUIRED_TOOL_NOT_AVAILABLE:required={required_name}")
            else:
                tool_specs = None
                tool_choice = None
            async for event in super().stream(
                messages,
                tool_specs,
                system_prompt,
                tool_choice=tool_choice,
                **kwargs,
            ):
                yield event

    return RequiredToolModel()


@dataclass
class LiveEvidence:
    """Non-secret evidence collected from a real invocation."""

    model_id: str = "amazon.nova-lite-v1:0"
    region: str = "unknown"
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    manager_agent_id: str = "launch-manager-live-preflight"
    reviewer_agent_id: str = "readiness-reviewer-live-preflight"
    manager_completed: bool = False
    reviewer_completed: bool = False
    agent_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    manager_cycle_limit: int = MANAGER_MAX_CYCLES
    reviewer_cycle_limit: int = REVIEWER_MAX_CYCLES

    def record(
        self,
        agent: str,
        tool_name: str,
        tool_use_id: str,
        status: str,
        latency_ms: int,
        output_sha256: str,
    ) -> None:
        self.tool_calls.append(
            {
                "sequence": len(self.tool_calls) + 1,
                "agent": agent,
                "tool": tool_name,
                "tool_use_id": tool_use_id,
                "status": status,
                "latency_ms": latency_ms,
                "output_sha256": output_sha256,
            }
        )


@dataclass
class LiveAnalysis:
    """Safe product result returned after a real two-agent invocation."""

    manager_explanation: str
    reviewer_report: dict[str, Any]
    evidence: LiveEvidence


def _json_result(tool_name: str, payload: dict[str, Any]) -> str:
    return json.dumps({"tool": tool_name, "status": "executed", **payload}, sort_keys=True)


def _safe_sha256(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return sha256(serialized.encode()).hexdigest()


def _package_version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "unavailable"


def _source_digest() -> tuple[list[str], str]:
    root = Path(__file__).resolve().parents[2]
    relative_files = [
        "pyproject.toml",
        "requirements-dev.lock",
        "scripts/preflight_live.py",
        "scripts/run_demo.py",
        "scripts/sanitize_junit.py",
        "src/store_ready/__init__.py",
        "src/store_ready/agents.py",
        "src/store_ready/domain.py",
        "src/store_ready/evidence.py",
        "src/store_ready/preflight.py",
        "src/store_ready/service.py",
        "src/store_ready/storage.py",
        "src/store_ready/web_app.py",
        "src/store_ready/templates/index.html",
        "src/store_ready/static/app.css",
        "src/store_ready/static/app.js",
        "tests/test_agents.py",
        "tests/test_domain.py",
        "tests/test_preflight.py",
        "tests/test_service.py",
        "tests/test_storage.py",
        "tests/test_web_app.py",
        "tests/test_rescue.py",
    ]
    digest = sha256()
    for relative in relative_files:
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update((root / relative).read_bytes())
        digest.update(b"\0")
    return relative_files, digest.hexdigest()


def _attach_agent_audit(
    agent: Any,
    model: Any,
    evidence: LiveEvidence,
    agent_name: str,
    after_tool_event: type[Any],
    after_invocation_event: type[Any],
) -> None:
    retried_tool_uses: set[str] = set()

    def after_tool(event: Any) -> None:
        tool_name = str(event.tool_use.get("name", "unknown"))
        tool_use_id = str(event.tool_use.get("toolUseId", "unknown"))
        result = event.result
        status = (
            str(result.get("status", "error"))
            if isinstance(result, dict) and event.exception is None
            else "error"
        )
        if status == "success":
            model.mark_tool_success(tool_name)
            evidence.record(
                agent_name,
                tool_name,
                tool_use_id,
                status,
                round((event.duration or 0) * 1_000),
                _safe_sha256(result),
            )
            return
        model.mark_tool_failed(tool_name)
        if tool_name == "readiness_reviewer":
            raise LivePreflightFailed("REVIEWER_AGENT_AS_TOOL_FAILED")
        if tool_name != "readiness_reviewer" and tool_use_id not in retried_tool_uses:
            retried_tool_uses.add(tool_use_id)
            event.retry = True

    def after_invocation(event: Any) -> None:
        if event.result is None:
            return
        summary = event.result.metrics.get_summary()
        usage = summary.get("accumulated_usage", {})
        evidence.agent_metrics[agent_name] = {
            "cycles": summary.get("total_cycles", 0),
            "latency_ms": round(float(summary.get("total_duration", 0)) * 1_000),
            "input_tokens": usage.get("inputTokens", 0),
            "output_tokens": usage.get("outputTokens", 0),
            "total_tokens": usage.get("totalTokens", 0),
            "stop_reason": str(event.result.stop_reason),
        }

    agent.add_hook(after_tool, after_tool_event)
    agent.add_hook(after_invocation, after_invocation_event)


def _deterministic_context() -> tuple[ProjectInput, tuple[LaunchTask, ...], tuple[float, ...]]:
    project = demo_project()
    return project, default_tasks(project), demo_budget_items()


def _project_snapshot(project: ProjectInput, budget_items: tuple[float, ...] | None) -> str:
    """Serialize immutable source input without Manager-derived calculations."""

    snapshot = json.dumps(
        {
            "store_type": project.store_type,
            "location": project.location,
            "budget": project.budget,
            "opening_date": project.opening_date.isoformat(),
            "acquired_documents": project.acquired_documents,
            "missing_documents": project.missing_documents,
            "completed_items": project.completed_items,
            "pending_items": project.pending_items,
            "budget_items": budget_items,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    if len(snapshot.encode()) > MAX_AGENT_INPUT_BYTES:
        raise LivePreflightFailed("AGENT_INPUT_LIMIT_EXCEEDED")
    return snapshot


def _context_from_snapshot(
    snapshot: str,
) -> tuple[ProjectInput, tuple[LaunchTask, ...], tuple[float, ...] | None]:
    """Recreate Reviewer inputs from source, never from Manager output."""

    payload = json.loads(snapshot)
    project = ProjectInput(
        store_type=payload["store_type"],
        location=payload["location"],
        budget=float(payload["budget"]),
        opening_date=date.fromisoformat(payload["opening_date"]),
        acquired_documents=tuple(payload["acquired_documents"]),
        missing_documents=tuple(payload["missing_documents"]),
        completed_items=tuple(payload["completed_items"]),
        pending_items=tuple(payload["pending_items"]),
    )
    budget_items = payload["budget_items"]
    parsed_budget = (
        tuple(float(item) for item in budget_items) if budget_items is not None else None
    )
    return project, default_tasks(project), parsed_budget


def _independent_report_from_snapshot(
    snapshot: str, untrusted_manager_output: Any = None
) -> dict[str, Any]:
    """Recompute the report while deliberately ignoring Manager-owned output."""

    del untrusted_manager_output
    project, tasks, budget_items = _context_from_snapshot(snapshot)
    return _report_payload_for(project, tasks, budget_items)


def _schedule_payload_for(
    project: ProjectInput, tasks: tuple[LaunchTask, ...]
) -> list[dict[str, Any]]:
    return [
        {
            "task_id": item.task_id,
            "name": item.name,
            "start_date": item.start_date.isoformat(),
            "due_date": item.due_date.isoformat(),
            "duration_days": item.duration_days,
            "critical": item.critical,
            "completed": item.completed,
        }
        for item in deterministic_critical_path(tasks, project.opening_date)
    ]


def _schedule_payload() -> list[dict[str, Any]]:
    project, tasks, _ = _deterministic_context()
    return _schedule_payload_for(project, tasks)


def _gap_payload_for(
    project: ProjectInput,
    tasks: tuple[LaunchTask, ...],
    budget_items: tuple[float, ...] | None,
) -> list[dict[str, str]]:
    return [
        {
            "kind": item.kind,
            "title": item.title,
            "detail": item.detail,
            "severity": item.severity,
        }
        for item in calculate_readiness(project, tasks, budget_items).gaps
    ]


def _gap_payload() -> list[dict[str, str]]:
    project, tasks, budget_items = _deterministic_context()
    return _gap_payload_for(project, tasks, budget_items)


def _report_payload_for(
    project: ProjectInput,
    tasks: tuple[LaunchTask, ...],
    budget_items: tuple[float, ...] | None,
) -> dict[str, Any]:
    result = calculate_readiness(project, tasks, budget_items)
    return {
        "score": result.score,
        "task_completion_percent": result.task_completion_percent,
        "budget_total": result.budget_total,
        "budget_overage": result.budget_overage,
        "delayed_days": result.delayed_days,
        "missing_documents": list(result.missing_documents),
        "schedule": _schedule_payload_for(project, tasks),
        "gaps": _gap_payload_for(project, tasks, budget_items),
        "review_mode": "independent-read-only",
    }


def _report_payload() -> dict[str, Any]:
    project, tasks, budget_items = _deterministic_context()
    return _report_payload_for(project, tasks, budget_items)


def _check_required_calls(evidence: LiveEvidence) -> None:
    required_manager = {
        "create_launch_plan",
        "calculate_critical_path",
        "detect_readiness_gaps",
        "readiness_reviewer",
    }
    required_reviewer = {
        "calculate_critical_path",
        "detect_readiness_gaps",
        "generate_readiness_report",
    }
    manager_calls = {
        item["tool"] for item in evidence.tool_calls if item["agent"] == "launch_manager"
    }
    reviewer_calls = {
        item["tool"] for item in evidence.tool_calls if item["agent"] == "readiness_reviewer"
    }
    if not required_manager <= manager_calls or not required_reviewer <= reviewer_calls:
        missing_manager = sorted(required_manager - manager_calls)
        missing_reviewer = sorted(required_reviewer - reviewer_calls)
        raise LivePreflightFailed(
            "LIVE_AGENT_TOOL_CALLS_INCOMPLETE:"
            f"manager={','.join(missing_manager) or 'none'};"
            f"reviewer={','.join(missing_reviewer) or 'none'}"
        )
    if evidence.manager_agent_id == evidence.reviewer_agent_id:
        raise LivePreflightFailed("LIVE_AGENT_IDS_NOT_DISTINCT")


def _independent_rescue_review(
    source_json: str,
    scenario_json: str,
    expected_hashes: dict[str, str],
    untrusted_manager_output: Any = None,
) -> dict[str, Any]:
    """Recompute from immutable inputs and fail closed on any server-side hash mismatch."""

    del untrusted_manager_output
    recomputed = recompute_rescue_from_snapshots(source_json, scenario_json)
    hashes = recomputed["hashes"]
    if any(hashes.get(name) != expected_hashes.get(name) for name in ("source", "shock", "result")):
        raise LivePreflightFailed("RESCUE_HASH_MISMATCH")
    return {
        **recomputed["result"],
        "hashes": hashes,
        "hash_match": True,
        "review_mode": "independent-read-only",
    }


def _check_rescue_required_calls(evidence: LiveEvidence) -> None:
    required_manager = {"simulate_opening_rescue", "readiness_reviewer"}
    required_reviewer = {
        "simulate_opening_rescue",
        "verify_rescue_hashes",
        "generate_rescue_review",
    }
    manager_calls = {
        item["tool"] for item in evidence.tool_calls if item["agent"] == "launch_manager"
    }
    reviewer_calls = {
        item["tool"] for item in evidence.tool_calls if item["agent"] == "readiness_reviewer"
    }
    if not required_manager <= manager_calls or not required_reviewer <= reviewer_calls:
        raise LivePreflightFailed("RESCUE_TOOL_CALLS_INCOMPLETE")
    if evidence.manager_agent_id == evidence.reviewer_agent_id:
        raise LivePreflightFailed("LIVE_AGENT_IDS_NOT_DISTINCT")


def run_live_analysis(
    config: PreflightConfig,
    project: ProjectInput,
    tasks: tuple[LaunchTask, ...],
    budget_items: tuple[float, ...] | None,
) -> LiveAnalysis:
    """Run the real Manager and Reviewer against one fictional project input."""

    try:
        from strands import Agent, tool
        from strands.hooks import AfterInvocationEvent, AfterToolCallEvent, BeforeToolCallEvent
        from strands.models import BedrockModel
    except ModuleNotFoundError as exc:
        raise LivePreflightFailed("P0_RUNTIME_REQUIRED: install boto3 and strands-agents") from exc

    evidence = LiveEvidence(
        model_id=config.model_id,
        region=config.region,
        manager_agent_id="launch-manager-live",
        reviewer_agent_id="readiness-reviewer-live",
    )
    reviewer_report: dict[str, Any] = {}
    source_snapshot = _project_snapshot(project, budget_items)

    def reviewer_context() -> tuple[ProjectInput, tuple[LaunchTask, ...], tuple[float, ...] | None]:
        return _context_from_snapshot(source_snapshot)

    @tool
    def create_launch_plan(project_summary: str) -> str:
        return _json_result(
            "create_launch_plan",
            {
                "summary_received": bool(project_summary),
                "schedule": _schedule_payload_for(project, tasks),
            },
        )

    @tool(name="calculate_critical_path")
    def manager_calculate_critical_path(project_summary: str) -> str:
        return _json_result(
            "calculate_critical_path",
            {"schedule": _schedule_payload_for(project, tasks), "calculation": "deterministic"},
        )

    @tool(name="detect_readiness_gaps")
    def manager_detect_readiness_gaps(project_summary: str) -> str:
        return _json_result(
            "detect_readiness_gaps",
            {"gaps": _gap_payload_for(project, tasks, budget_items)},
        )

    @tool(name="calculate_critical_path")
    def reviewer_calculate_critical_path() -> str:
        """Recalculate the critical path from the bound immutable source snapshot."""

        reviewed_project, reviewed_tasks, _ = reviewer_context()
        return _json_result(
            "calculate_critical_path",
            {
                "schedule": _schedule_payload_for(reviewed_project, reviewed_tasks),
                "calculation": "independent-read-only",
            },
        )

    @tool(name="detect_readiness_gaps")
    def reviewer_detect_readiness_gaps() -> str:
        """Recalculate readiness gaps from the bound immutable source snapshot."""

        reviewed_project, reviewed_tasks, reviewed_budget = reviewer_context()
        return _json_result(
            "detect_readiness_gaps",
            {
                "gaps": _gap_payload_for(reviewed_project, reviewed_tasks, reviewed_budget),
                "calculation": "independent-read-only",
            },
        )

    @tool
    def generate_readiness_report() -> str:
        """Build the independent report from the bound immutable source snapshot."""

        reviewer_report.update(
            _independent_report_from_snapshot(
                source_snapshot,
                untrusted_manager_output={},
            )
        )
        return _json_result("generate_readiness_report", {"report": reviewer_report})

    reviewer_model = _required_tool_model(
        BedrockModel,
        config,
        (
            "calculate_critical_path",
            "detect_readiness_gaps",
            "generate_readiness_report",
        ),
        maximum_cycles=REVIEWER_MAX_CYCLES,
    )
    reviewer = Agent(
        agent_id=evidence.reviewer_agent_id,
        name="readiness_reviewer",
        description="Recalculates the original fictional project without writing state.",
        model=reviewer_model,
        tools=[
            reviewer_calculate_critical_path,
            reviewer_detect_readiness_gaps,
            generate_readiness_report,
        ],
        system_prompt=(
            "You are the Readiness Reviewer. Re-read the original fictional project data, "
            "independently call calculate_critical_path, detect_readiness_gaps, and "
            "generate_readiness_report. Never trust a manager summary, write state, "
            "approve anything, or call record_decision. After all three tools succeed, "
            "you must stop calling tools and reply with exactly REVIEW_COMPLETE and no "
            "additional text."
        ),
        callback_handler=None,
    )
    manager_model = _required_tool_model(
        BedrockModel,
        config,
        (
            "create_launch_plan",
            "calculate_critical_path",
            "detect_readiness_gaps",
            "readiness_reviewer",
        ),
        maximum_cycles=MANAGER_MAX_CYCLES,
    )
    manager = Agent(
        agent_id=evidence.manager_agent_id,
        name="launch_manager",
        description="Orchestrates a launch plan and requests an independent review.",
        model=manager_model,
        tools=[
            create_launch_plan,
            manager_calculate_critical_path,
            manager_detect_readiness_gaps,
            reviewer.as_tool(name="readiness_reviewer", description="Run an independent review."),
        ],
        system_prompt=(
            "You are the Launch Manager. Call create_launch_plan, calculate_critical_path, "
            "detect_readiness_gaps, then readiness_reviewer for the original fictional "
            "project. Explain results but never approve a human decision or call "
            "record_decision. After the tools succeed, explain the key risks in no more "
            "than 150 words. Reply in Traditional Chinese as used in Taiwan."
        ),
        callback_handler=None,
    )

    _attach_agent_audit(
        reviewer,
        reviewer_model,
        evidence,
        "readiness_reviewer",
        AfterToolCallEvent,
        AfterInvocationEvent,
    )
    _attach_agent_audit(
        manager,
        manager_model,
        evidence,
        "launch_manager",
        AfterToolCallEvent,
        AfterInvocationEvent,
    )

    def bind_reviewer_to_source(event: Any) -> None:
        if event.tool_use.get("name") == "readiness_reviewer":
            event.tool_use["input"] = {"input": source_snapshot}

    manager.add_hook(bind_reviewer_to_source, BeforeToolCallEvent)
    summary = source_snapshot
    cancel_signal = threading.Event()
    timeout = threading.Timer(LIVE_TIMEOUT_SECONDS, cancel_signal.set)
    timeout.start()
    try:
        manager_response = manager(
            summary,
            cancel_signal=cancel_signal,
            limits={
                "turns": MANAGER_MAX_CYCLES,
                "output_tokens": MANAGER_MAX_CYCLES * MAX_MODEL_OUTPUT_TOKENS,
            },
        )
    except LivePreflightFailed:
        raise
    except Exception as exc:  # noqa: BLE001 - SDK boundary is converted to safe status.
        raise LivePreflightFailed(
            f"LIVE_AGENT_EXECUTION_FAILED:{_safe_exception_type_chain(exc)}"
        ) from exc
    finally:
        timeout.cancel()
    if cancel_signal.is_set():
        raise LivePreflightFailed("LIVE_AGENT_TIMEOUT")
    evidence.manager_completed = True
    evidence.reviewer_completed = any(
        item["agent"] == "readiness_reviewer" for item in evidence.tool_calls
    )
    _check_required_calls(evidence)
    return LiveAnalysis(str(manager_response), reviewer_report, evidence)


def run_live_rescue_review(
    config: PreflightConfig,
    source_json: str,
    scenario_json: str,
    expected_hashes: dict[str, str],
) -> LiveAnalysis:
    """Run a bounded two-Agent review of one immutable rescue simulation."""

    try:
        from strands import Agent, tool
        from strands.hooks import AfterInvocationEvent, AfterToolCallEvent, BeforeToolCallEvent
        from strands.models import BedrockModel
    except ModuleNotFoundError as exc:
        raise LivePreflightFailed("P0_RUNTIME_REQUIRED: install boto3 and strands-agents") from exc

    if len(source_json.encode()) + len(scenario_json.encode()) > MAX_AGENT_INPUT_BYTES:
        raise LivePreflightFailed("AGENT_INPUT_LIMIT_EXCEEDED")
    evidence = LiveEvidence(
        model_id=config.model_id,
        region=config.region,
        manager_agent_id="launch-manager-rescue-live",
        reviewer_agent_id="readiness-reviewer-rescue-live",
        manager_cycle_limit=RESCUE_MANAGER_MAX_CYCLES,
        reviewer_cycle_limit=RESCUE_REVIEWER_MAX_CYCLES,
    )
    reviewer_report: dict[str, Any] = {}

    def independent_result() -> dict[str, Any]:
        return _independent_rescue_review(source_json, scenario_json, expected_hashes)

    @tool(name="simulate_opening_rescue")
    def manager_simulate_opening_rescue(scenario_summary: str) -> str:
        """Run the deterministic rescue simulator from bound validated inputs."""

        del scenario_summary
        result = recompute_rescue_from_snapshots(source_json, scenario_json)
        return _json_result(
            "simulate_opening_rescue",
            {"result": result["result"], "hashes": result["hashes"]},
        )

    @tool(name="simulate_opening_rescue")
    def reviewer_simulate_opening_rescue() -> str:
        """Independently rerun the simulator without accepting Manager output."""

        result = independent_result()
        return _json_result(
            "simulate_opening_rescue",
            {
                "projected_delay_workdays": result["projected_delay_workdays"],
                "strategies": result["strategies"],
                "calculation": "independent-read-only",
            },
        )

    @tool(name="verify_rescue_hashes")
    def reviewer_verify_rescue_hashes() -> str:
        """Verify source, shock and deterministic result hashes on the server."""

        result = independent_result()
        return _json_result(
            "verify_rescue_hashes",
            {"hashes": result["hashes"], "hash_match": True},
        )

    @tool(name="generate_rescue_review")
    def generate_rescue_review() -> str:
        """Publish the read-only independently recomputed rescue review."""

        reviewer_report.update(independent_result())
        return _json_result("generate_rescue_review", {"report": reviewer_report})

    reviewer_model = _required_tool_model(
        BedrockModel,
        config,
        (
            "simulate_opening_rescue",
            "verify_rescue_hashes",
            "generate_rescue_review",
        ),
        maximum_cycles=RESCUE_REVIEWER_MAX_CYCLES,
    )
    reviewer = Agent(
        agent_id=evidence.reviewer_agent_id,
        name="readiness_reviewer",
        description="Independently recalculates a bound rescue scenario without writing state.",
        model=reviewer_model,
        tools=[
            reviewer_simulate_opening_rescue,
            reviewer_verify_rescue_hashes,
            generate_rescue_review,
        ],
        system_prompt=(
            "You are the Readiness Reviewer. Independently call simulate_opening_rescue, "
            "verify_rescue_hashes, and generate_rescue_review from the immutable source "
            "and shock. Never accept Manager calculations, write state, select a strategy, "
            "approve anything, or call record_decision. After all tools succeed, reply "
            "with exactly RESCUE_REVIEW_COMPLETE and no additional text."
        ),
        callback_handler=None,
    )
    manager_model = _required_tool_model(
        BedrockModel,
        config,
        ("simulate_opening_rescue", "readiness_reviewer"),
        maximum_cycles=RESCUE_MANAGER_MAX_CYCLES,
    )
    manager = Agent(
        agent_id=evidence.manager_agent_id,
        name="launch_manager",
        description="Explains a deterministic rescue simulation and requests independent review.",
        model=manager_model,
        tools=[
            manager_simulate_opening_rescue,
            reviewer.as_tool(
                name="readiness_reviewer",
                description="Independently review the immutable rescue simulation.",
            ),
        ],
        system_prompt=(
            "You are the Launch Manager. Call simulate_opening_rescue, then call "
            "readiness_reviewer. Explain only the deterministic trade-offs in Traditional "
            "Chinese. Never invent dates or costs, select a strategy, approve a decision, "
            "write state, or call record_decision. Keep the final explanation under 120 words."
        ),
        callback_handler=None,
    )
    _attach_agent_audit(
        reviewer,
        reviewer_model,
        evidence,
        "readiness_reviewer",
        AfterToolCallEvent,
        AfterInvocationEvent,
    )
    _attach_agent_audit(
        manager,
        manager_model,
        evidence,
        "launch_manager",
        AfterToolCallEvent,
        AfterInvocationEvent,
    )

    reviewer_binding = json.dumps(
        {
            "source_hash": expected_hashes.get("source"),
            "shock_hash": expected_hashes.get("shock"),
            "instruction": "recompute from server-bound immutable snapshots",
        },
        sort_keys=True,
    )

    def bind_reviewer_to_rescue_source(event: Any) -> None:
        if event.tool_use.get("name") == "readiness_reviewer":
            event.tool_use["input"] = {"input": reviewer_binding}

    manager.add_hook(bind_reviewer_to_rescue_source, BeforeToolCallEvent)
    summary = json.dumps(
        {
            "source_hash": expected_hashes.get("source"),
            "shock_hash": expected_hashes.get("shock"),
            "mode": "opening-rescue",
        },
        sort_keys=True,
    )
    cancel_signal = threading.Event()
    timeout = threading.Timer(LIVE_TIMEOUT_SECONDS, cancel_signal.set)
    timeout.start()
    try:
        manager_response = manager(
            summary,
            cancel_signal=cancel_signal,
            limits={
                "turns": RESCUE_MANAGER_MAX_CYCLES,
                "output_tokens": RESCUE_MANAGER_MAX_CYCLES * MAX_MODEL_OUTPUT_TOKENS,
            },
        )
    except LivePreflightFailed:
        raise
    except Exception as exc:  # noqa: BLE001 - SDK boundary is converted to safe status.
        raise LivePreflightFailed(
            f"LIVE_RESCUE_EXECUTION_FAILED:{_safe_exception_type_chain(exc)}"
        ) from exc
    finally:
        timeout.cancel()
    if cancel_signal.is_set():
        raise LivePreflightFailed("LIVE_AGENT_TIMEOUT")
    evidence.manager_completed = True
    evidence.reviewer_completed = any(
        item["agent"] == "readiness_reviewer" for item in evidence.tool_calls
    )
    _check_rescue_required_calls(evidence)
    return LiveAnalysis(str(manager_response), reviewer_report, evidence)


def run_live_preflight(config: PreflightConfig) -> LiveEvidence:
    """Run two real Strands agents and verify their required tool calls."""

    try:
        from strands import Agent, tool
        from strands.hooks import AfterInvocationEvent, AfterToolCallEvent, BeforeToolCallEvent
        from strands.models import BedrockModel
    except ModuleNotFoundError as exc:
        raise LivePreflightFailed("P0_RUNTIME_REQUIRED: install boto3 and strands-agents") from exc

    evidence = LiveEvidence(model_id=config.model_id, region=config.region)

    @tool
    def create_launch_plan(project_summary: str) -> str:
        """Create a launch-plan draft from the supplied fictional project summary."""

        return _json_result(
            "create_launch_plan",
            {
                "summary_received": bool(project_summary),
                "schedule": _schedule_payload(),
            },
        )

    @tool(name="calculate_critical_path")
    def manager_calculate_critical_path(project_summary: str) -> str:
        """Calculate the critical path using the deterministic planner boundary."""

        return _json_result(
            "calculate_critical_path",
            {"schedule": _schedule_payload(), "calculation": "deterministic"},
        )

    @tool(name="detect_readiness_gaps")
    def manager_detect_readiness_gaps(project_summary: str) -> str:
        """Detect document, budget and readiness gaps from the supplied summary."""

        return _json_result("detect_readiness_gaps", {"gaps": _gap_payload()})

    def reviewer_tools() -> tuple[Any, Any, Any]:
        @tool(name="calculate_critical_path")
        def calculate_critical_path() -> str:
            """Calculate the critical path independently from the original summary."""

            return _json_result(
                "calculate_critical_path",
                {"schedule": _schedule_payload(), "calculation": "independent-read-only"},
            )

        @tool(name="detect_readiness_gaps")
        def detect_readiness_gaps() -> str:
            """Detect readiness gaps independently from the original summary."""

            return _json_result(
                "detect_readiness_gaps",
                {"gaps": _gap_payload(), "calculation": "independent-read-only"},
            )

        @tool
        def generate_readiness_report() -> str:
            """Generate a read-only readiness report from independently checked data."""

            return _json_result("generate_readiness_report", {"report": _report_payload()})

        return calculate_critical_path, detect_readiness_gaps, generate_readiness_report

    reviewer_calculate, reviewer_detect, reviewer_report = reviewer_tools()

    reviewer_model = _required_tool_model(
        BedrockModel,
        config,
        (
            "calculate_critical_path",
            "detect_readiness_gaps",
            "generate_readiness_report",
        ),
        maximum_cycles=REVIEWER_MAX_CYCLES,
    )
    reviewer = Agent(
        agent_id=evidence.reviewer_agent_id,
        name="readiness_reviewer",
        description="Independently rechecks launch readiness and never changes project state.",
        model=reviewer_model,
        tools=[reviewer_calculate, reviewer_detect, reviewer_report],
        system_prompt=(
            "You are the Readiness Reviewer. Independently call calculate_critical_path, "
            "detect_readiness_gaps, and generate_readiness_report. Re-read the original "
            "fictional project summary; do not trust any manager summary. Never approve, "
            "write state, or call record_decision. After all three tools succeed, reply "
            "with exactly REVIEW_COMPLETE and no additional text."
        ),
        callback_handler=None,
    )
    manager_model = _required_tool_model(
        BedrockModel,
        config,
        (
            "create_launch_plan",
            "calculate_critical_path",
            "detect_readiness_gaps",
            "readiness_reviewer",
        ),
        maximum_cycles=MANAGER_MAX_CYCLES,
    )
    manager = Agent(
        agent_id=evidence.manager_agent_id,
        name="launch_manager",
        description="Builds a launch plan and requests an independent readiness review.",
        model=manager_model,
        tools=[
            create_launch_plan,
            manager_calculate_critical_path,
            manager_detect_readiness_gaps,
            reviewer.as_tool(
                name="readiness_reviewer", description="Run an independent read-only review."
            ),
        ],
        system_prompt=(
            "You are the Launch Manager. For the fictional project summary, call "
            "create_launch_plan, calculate_critical_path, detect_readiness_gaps, then "
            "readiness_reviewer. Do not call record_decision and do not claim a human "
            "approval. Do not answer until all four tool calls have completed, then reply "
            "with exactly MANAGER_COMPLETE and no additional text."
        ),
        callback_handler=None,
    )

    _attach_agent_audit(
        reviewer,
        reviewer_model,
        evidence,
        "readiness_reviewer",
        AfterToolCallEvent,
        AfterInvocationEvent,
    )
    _attach_agent_audit(
        manager,
        manager_model,
        evidence,
        "launch_manager",
        AfterToolCallEvent,
        AfterInvocationEvent,
    )

    def bind_reviewer_to_source(event: Any) -> None:
        if event.tool_use.get("name") == "readiness_reviewer":
            event.tool_use["input"] = {
                "input": (
                    "Fictional source only: neighborhood coffee shop in Taipei; budget "
                    "NT$800000; opening date 2026-10-30. Recompute independently."
                )
            }

    manager.add_hook(bind_reviewer_to_source, BeforeToolCallEvent)

    cancel_signal = threading.Event()
    timeout = threading.Timer(LIVE_TIMEOUT_SECONDS, cancel_signal.set)
    timeout.start()
    try:
        manager(
            "Fictional demo only: a neighborhood coffee shop in Taipei, budget NT$800000, "
            "opening date 2026-10-30. Return a short acknowledgement after the required "
            "tool calls.",
            cancel_signal=cancel_signal,
            limits={
                "turns": MANAGER_MAX_CYCLES,
                "output_tokens": MANAGER_MAX_CYCLES * MAX_MODEL_OUTPUT_TOKENS,
            },
        )
    except LivePreflightFailed:
        raise
    except Exception as exc:  # noqa: BLE001 - boundary converts SDK errors to safe status.
        raise LivePreflightFailed(
            f"LIVE_AGENT_EXECUTION_FAILED:{_safe_exception_type_chain(exc)}"
        ) from exc
    finally:
        timeout.cancel()
    if cancel_signal.is_set():
        raise LivePreflightFailed("LIVE_AGENT_TIMEOUT")

    evidence.manager_completed = True
    evidence.reviewer_completed = any(
        item["agent"] == "readiness_reviewer" for item in evidence.tool_calls
    )
    _check_required_calls(evidence)
    return evidence


def evidence_document(evidence: LiveEvidence) -> dict[str, Any]:
    """Return a secret-free JSON-compatible evidence document."""

    source_files, source_sha256 = _source_digest()
    return {
        "recorded_at": datetime.now(UTC).isoformat(),
        "model_id": evidence.model_id,
        "region": evidence.region,
        "runtime": {
            "python": platform.python_version(),
            "strands_agents": _package_version("strands-agents"),
            "boto3": _package_version("boto3"),
            "botocore": _package_version("botocore"),
        },
        "source_files": source_files,
        "source_sha256": source_sha256,
        "manager_agent_id": evidence.manager_agent_id,
        "reviewer_agent_id": evidence.reviewer_agent_id,
        "manager_completed": evidence.manager_completed,
        "reviewer_completed": evidence.reviewer_completed,
        "tool_calls": evidence.tool_calls,
        "agent_metrics": evidence.agent_metrics,
        "limits": {
            "manager_cycles": evidence.manager_cycle_limit,
            "reviewer_cycles": evidence.reviewer_cycle_limit,
            "model_output_tokens_per_cycle": MAX_MODEL_OUTPUT_TOKENS,
            "overall_timeout_seconds": LIVE_TIMEOUT_SECONDS,
            "tool_retry_per_call": 1,
            "bedrock_connect_timeout_seconds": BEDROCK_CONNECT_TIMEOUT_SECONDS,
            "bedrock_read_timeout_seconds": BEDROCK_READ_TIMEOUT_SECONDS,
            "bedrock_total_attempts": 1,
        },
        "secrets_recorded": False,
    }
