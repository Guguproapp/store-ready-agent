import unittest
from types import SimpleNamespace
from typing import Any

from store_ready.agents import (
    LiveEvidence,
    LivePreflightFailed,
    _attach_agent_audit,
    _context_from_snapshot,
    _gap_payload,
    _independent_report_from_snapshot,
    _project_snapshot,
    _report_payload,
    _RequiredToolSequence,
    _safe_exception_type_chain,
    _schedule_payload,
    evidence_document,
)


class AgentBoundaryTests(unittest.TestCase):
    def test_safe_exception_chain_exposes_types_without_messages(self) -> None:
        class WrapperError(RuntimeError):
            def __init__(self, original_exception: BaseException) -> None:
                self.original_exception = original_exception
                super().__init__("sensitive-provider-message")

        chain = _safe_exception_type_chain(WrapperError(TimeoutError("secret detail")))
        self.assertEqual(chain, "WrapperError:TimeoutError")
        self.assertNotIn("secret", chain)

        safe_failure = WrapperError(LivePreflightFailed("MODEL_CYCLE_LIMIT_EXCEEDED"))
        self.assertEqual(
            _safe_exception_type_chain(safe_failure),
            "WrapperError:LivePreflightFailed[MODEL_CYCLE_LIMIT_EXCEEDED]",
        )

    def test_required_tool_advances_only_after_success(self) -> None:
        sequence = _RequiredToolSequence(("first", "second"), maximum_cycles=4)
        self.assertEqual(sequence.required_for_next_cycle(), "first")
        sequence.mark_failed("first")
        self.assertEqual(sequence.required_for_next_cycle(), "first")
        sequence.mark_success("first")
        self.assertEqual(sequence.required_for_next_cycle(), "second")
        sequence.mark_success("second")
        self.assertIsNone(sequence.required_for_next_cycle())

    def test_required_tool_cycle_limit_fails_closed(self) -> None:
        sequence = _RequiredToolSequence(("first",), maximum_cycles=2)
        sequence.required_for_next_cycle()
        sequence.required_for_next_cycle()
        with self.assertRaisesRegex(LivePreflightFailed, "MODEL_CYCLE_LIMIT_EXCEEDED"):
            sequence.required_for_next_cycle()

    def test_failed_tool_retry_does_not_advance_or_fabricate_evidence(self) -> None:
        class StubAgent:
            def __init__(self) -> None:
                self.hooks: dict[object, Any] = {}

            def add_hook(self, callback: object, event_type: object) -> None:
                self.hooks[event_type] = callback

        class ToolEvent:
            pass

        class InvocationEvent:
            pass

        class StubModel:
            def __init__(self) -> None:
                self.sequence = _RequiredToolSequence(("first",), 3)

            def mark_tool_success(self, tool_name: str) -> None:
                self.sequence.mark_success(tool_name)

            def mark_tool_failed(self, tool_name: str) -> None:
                self.sequence.mark_failed(tool_name)

        agent = StubAgent()
        model = StubModel()
        evidence = LiveEvidence()
        _attach_agent_audit(agent, model, evidence, "launch_manager", ToolEvent, InvocationEvent)
        callback = agent.hooks[ToolEvent]
        failure = SimpleNamespace(
            tool_use={"name": "first", "toolUseId": "tool-1"},
            result={"status": "error"},
            exception=RuntimeError("synthetic failure"),
            duration=0.01,
            retry=False,
        )
        callback(failure)
        self.assertTrue(failure.retry)
        self.assertEqual(model.sequence.index, 0)
        self.assertEqual(evidence.tool_calls, [])
        success = SimpleNamespace(
            tool_use={"name": "first", "toolUseId": "tool-1"},
            result={"status": "success", "content": "fictional"},
            exception=None,
            duration=0.01,
            retry=False,
        )
        callback(success)
        self.assertEqual(model.sequence.index, 1)
        self.assertEqual(len(evidence.tool_calls), 1)
        self.assertEqual(evidence.tool_calls[0]["status"], "success")

    def test_failed_agent_as_tool_is_not_reentered_while_locked(self) -> None:
        class StubAgent:
            def __init__(self) -> None:
                self.hooks: dict[object, Any] = {}

            def add_hook(self, callback: object, event_type: object) -> None:
                self.hooks[event_type] = callback

        class ToolEvent:
            pass

        class InvocationEvent:
            pass

        class StubModel:
            def mark_tool_success(self, tool_name: str) -> None:
                return

            def mark_tool_failed(self, tool_name: str) -> None:
                return

        agent = StubAgent()
        _attach_agent_audit(
            agent, StubModel(), LiveEvidence(), "launch_manager", ToolEvent, InvocationEvent
        )
        failure = SimpleNamespace(
            tool_use={"name": "readiness_reviewer", "toolUseId": "agent-tool-1"},
            result={"status": "error"},
            exception=RuntimeError("synthetic failure"),
            duration=0.01,
            retry=False,
        )
        with self.assertRaisesRegex(LivePreflightFailed, "REVIEWER_AGENT_AS_TOOL_FAILED"):
            agent.hooks[ToolEvent](failure)
        self.assertFalse(failure.retry)

    def test_agent_input_and_runtime_limits_are_evidenced(self) -> None:
        from dataclasses import replace

        from store_ready.domain import demo_budget_items, demo_project

        with self.assertRaisesRegex(LivePreflightFailed, "AGENT_INPUT_LIMIT_EXCEEDED"):
            _project_snapshot(replace(demo_project(), location="地" * 20_000), demo_budget_items())
        limits = evidence_document(LiveEvidence())["limits"]
        self.assertIn(
            "src/store_ready/__init__.py", evidence_document(LiveEvidence())["source_files"]
        )
        self.assertEqual(limits["manager_cycles"], 6)
        self.assertEqual(limits["reviewer_cycles"], 5)
        self.assertEqual(limits["model_output_tokens_per_cycle"], 1_024)
        self.assertEqual(limits["overall_timeout_seconds"], 120)
        self.assertEqual(limits["tool_retry_per_call"], 1)
        self.assertEqual(limits["bedrock_connect_timeout_seconds"], 3)
        self.assertEqual(limits["bedrock_read_timeout_seconds"], 20)
        self.assertEqual(limits["bedrock_total_attempts"], 1)

    def test_reviewer_recomputes_from_original_snapshot(self) -> None:
        from store_ready.domain import (
            calculate_readiness,
            default_tasks,
            demo_budget_items,
            demo_project,
        )

        project = demo_project()
        snapshot = _project_snapshot(project, demo_budget_items())
        tampered_manager_result = {"score": 100, "critical": []}
        reviewed_project, reviewed_tasks, reviewed_budget = _context_from_snapshot(snapshot)
        reviewed = calculate_readiness(reviewed_project, reviewed_tasks, reviewed_budget)
        report = _independent_report_from_snapshot(snapshot, tampered_manager_result)
        self.assertEqual(tampered_manager_result["score"], 100)
        self.assertEqual(reviewed.score, 43)
        self.assertEqual(report["score"], 43)
        self.assertNotEqual(report["score"], tampered_manager_result["score"])
        self.assertEqual(reviewed_tasks, default_tasks(reviewed_project))

    def test_preflight_tool_payloads_use_real_deterministic_results(self) -> None:
        schedule = _schedule_payload()
        gaps = _gap_payload()
        report = _report_payload()

        self.assertEqual(schedule[-1]["task_id"], "inspection")
        self.assertTrue(schedule[-1]["critical"])
        self.assertEqual({item["kind"] for item in gaps}, {"document", "budget", "training"})
        self.assertEqual(report["score"], 43)
        self.assertEqual(report["review_mode"], "independent-read-only")

    def test_evidence_has_distinct_agent_ids_and_no_secret_field(self) -> None:
        document = evidence_document(LiveEvidence())
        self.assertNotEqual(document["manager_agent_id"], document["reviewer_agent_id"])
        self.assertFalse(document["secrets_recorded"])
        self.assertNotIn("record_decision", str(document))
        self.assertIn("runtime", document)


if __name__ == "__main__":
    unittest.main()
