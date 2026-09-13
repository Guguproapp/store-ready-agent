"""Application service for creating a fictional launch-readiness analysis."""

from __future__ import annotations

import json
import math
import sqlite3
from collections.abc import Mapping
from dataclasses import asdict
from datetime import date
from hashlib import sha256
from typing import Any
from uuid import uuid4

from .domain import (
    MAX_MONEY_TWD,
    LaunchTask,
    ProjectInput,
    RescueScenario,
    calculate_readiness,
    calculate_task_timing,
    default_tasks,
    simulate_opening_rescue,
)
from .storage import prune_demo_projects, seed_project

MAX_STORE_TYPE_LENGTH = 80
MAX_LOCATION_LENGTH = 160
MAX_LIST_ITEMS = 50
MAX_LIST_ITEM_LENGTH = 160
MAX_BUDGET_ITEMS = 50
MAX_BUDGET_AMOUNT = MAX_MONEY_TWD
MAX_STORED_DEMO_PROJECTS = 500
DEMO_DATA_TTL_HOURS = 2
MIN_OPENING_DATE = date(2000, 1, 1)
MAX_OPENING_DATE = date(2100, 12, 31)


def _strings(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key, [])
    if (
        not isinstance(value, list)
        or len(value) > MAX_LIST_ITEMS
        or not all(
            isinstance(item, str) and item.strip() and len(item.strip()) <= MAX_LIST_ITEM_LENGTH
            for item in value
        )
    ):
        raise ValueError(f"INVALID_{key.upper()}")
    return tuple(item.strip() for item in value)


def parse_project_payload(payload: Mapping[str, Any]) -> ProjectInput:
    """Validate untrusted form/API input without contacting external services."""

    store_type = payload.get("store_type")
    location = payload.get("location")
    if not isinstance(store_type, str) or not store_type.strip():
        raise ValueError("INVALID_STORE_TYPE")
    if len(store_type.strip()) > MAX_STORE_TYPE_LENGTH:
        raise ValueError("STORE_TYPE_TOO_LONG")
    if not isinstance(location, str) or not location.strip():
        raise ValueError("INVALID_LOCATION")
    if len(location.strip()) > MAX_LOCATION_LENGTH:
        raise ValueError("LOCATION_TOO_LONG")
    try:
        budget = float(payload["budget"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("INVALID_BUDGET") from exc
    try:
        opening_date = date.fromisoformat(str(payload["opening_date"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("INVALID_OPENING_DATE") from exc
    if not math.isfinite(budget) or budget <= 0 or budget > MAX_BUDGET_AMOUNT:
        raise ValueError("INVALID_BUDGET")
    if not MIN_OPENING_DATE <= opening_date <= MAX_OPENING_DATE:
        raise ValueError("INVALID_OPENING_DATE")
    acquired_documents = _strings(payload, "acquired_documents")
    missing_documents = _strings(payload, "missing_documents")
    completed_items = _strings(payload, "completed_items")
    pending_items = _strings(payload, "pending_items")
    if set(acquired_documents) & set(missing_documents):
        raise ValueError("CONTRADICTORY_DOCUMENT_STATUS")
    if set(completed_items) & set(pending_items):
        raise ValueError("CONTRADICTORY_TASK_STATUS")
    return ProjectInput(
        store_type=store_type.strip(),
        location=location.strip(),
        budget=budget,
        opening_date=opening_date,
        acquired_documents=acquired_documents,
        missing_documents=missing_documents,
        completed_items=completed_items,
        pending_items=pending_items,
    )


def _budget_items(payload: Mapping[str, Any]) -> tuple[float, ...] | None:
    value = payload.get("budget_items")
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or len(value) > MAX_BUDGET_ITEMS
        or not all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(float(item))
            and float(item) <= MAX_BUDGET_AMOUNT
            for item in value
        )
    ):
        raise ValueError("INVALID_BUDGET_ITEMS")
    items = tuple(float(item) for item in value)
    if any(item < 0 for item in items) or not math.isfinite(sum(items)):
        raise ValueError("INVALID_BUDGET_ITEMS")
    return items or None


def result_json(
    project: ProjectInput,
    result: Any,
    project_id: str,
    tasks: tuple[LaunchTask, ...],
) -> dict[str, Any]:
    task_by_id = {task.task_id: task for task in tasks}
    timing_by_id = {
        item.task_id: item for item in calculate_task_timing(tasks, project.opening_date)
    }
    critical_path = [item.task_id for item in result.schedule if item.critical]
    known_task_names = set(task.name for task in tasks)
    unmapped_pending = [item for item in project.pending_items if item not in known_task_names]
    budget_available = result.budget_total is not None
    return {
        "project_id": project_id,
        "project": {
            "store_type": project.store_type,
            "location": project.location,
            "budget": project.budget,
            "opening_date": project.opening_date.isoformat(),
            "acquired_documents": list(project.acquired_documents),
            "missing_documents": list(project.missing_documents),
            "completed_items": list(project.completed_items),
            "pending_items": list(project.pending_items),
        },
        "status": "DETERMINISTIC_DEMO_ONLY",
        "report_available": False,
        "score": result.score,
        "score_status": "complete" if budget_available else "provisional",
        "task_completion_percent": result.task_completion_percent,
        "missing_documents": list(result.missing_documents),
        "unmapped_pending_items": unmapped_pending,
        "budget_data_status": "provided" if budget_available else "insufficient",
        "budget_total": result.budget_total,
        "budget_overage": result.budget_overage,
        "budget_remaining": (
            max(project.budget - result.budget_total, 0) if budget_available else None
        ),
        "delayed_days": result.delayed_days,
        "critical_path": critical_path,
        "gaps": [finding.__dict__ for finding in result.gaps],
        "schedule": [
            {
                **item.__dict__,
                "start_date": item.start_date.isoformat(),
                "due_date": item.due_date.isoformat(),
                "category": task_by_id[item.task_id].category,
                "depends_on": list(task_by_id[item.task_id].depends_on),
                "depends_on_names": [
                    task_by_id[dependency].name
                    for dependency in task_by_id[item.task_id].depends_on
                ],
                "status": "completed" if item.completed else "pending",
                "earliest_completion": timing_by_id[item.task_id].earliest_completion.isoformat(),
                "latest_safe_completion": timing_by_id[
                    item.task_id
                ].latest_safe_completion.isoformat(),
                "slack_workdays": timing_by_id[item.task_id].slack_workdays,
            }
            for item in result.schedule
        ],
        "approval_request": {
            "title": "確認預算、文件與開幕時程風險",
            "status": "pending",
            "human_only": True,
        },
    }


def analyze_payload(
    payload: Mapping[str, Any], connection: sqlite3.Connection | None = None
) -> dict[str, Any]:
    """Calculate a result without claiming an AI invocation."""

    project = parse_project_payload(payload)
    tasks = default_tasks(project)
    budget_items = _budget_items(payload)
    result = calculate_readiness(project, tasks, budget_items)
    project_id = uuid4().hex
    output = result_json(project, result, project_id, tasks)
    if connection is not None:
        prune_demo_projects(
            connection,
            retain=MAX_STORED_DEMO_PROJECTS - 1,
            ttl_hours=DEMO_DATA_TTL_HOURS,
        )
        seed_project(connection, project_id, project, tasks)
        connection.executemany(
            "INSERT INTO document_requirement(project_id, name, status) VALUES (?, ?, ?)",
            (
                (project_id, item, "acquired" if item in project.acquired_documents else "missing")
                for item in project.acquired_documents + project.missing_documents
            ),
        )
        connection.executemany(
            "INSERT INTO budget_item(project_id, name, amount) VALUES (?, ?, ?)",
            (
                (project_id, f"預算項目 {index}", amount)
                for index, amount in enumerate(budget_items or (), 1)
            ),
        )
        connection.executemany(
            "INSERT INTO risk_finding(project_id, kind, title, detail, severity) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                (project_id, item.kind, item.title, item.detail, item.severity)
                for item in result.gaps
            ),
        )
        approval = connection.execute(
            "INSERT INTO approval_request(project_id, title) VALUES (?, ?)",
            (project_id, output["approval_request"]["title"]),
        )
        output["approval_request"]["id"] = approval.lastrowid
        output["report_available"] = True
        connection.execute(
            "INSERT INTO audit_event(project_id, event_type, detail) VALUES (?, ?, ?)",
            (project_id, "deterministic_analysis_completed", "deterministic tools completed"),
        )
        connection.execute(
            "INSERT INTO readiness_report(project_id, source, score, content_json) "
            "VALUES (?, ?, ?, ?)",
            (
                project_id,
                "deterministic_demo",
                result.score,
                json.dumps(output, ensure_ascii=False),
            ),
        )
        connection.commit()
    return output


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _project_dict(project: ProjectInput) -> dict[str, Any]:
    return {
        "store_type": project.store_type,
        "location": project.location,
        "budget": project.budget,
        "opening_date": project.opening_date.isoformat(),
        "acquired_documents": list(project.acquired_documents),
        "missing_documents": list(project.missing_documents),
        "completed_items": list(project.completed_items),
        "pending_items": list(project.pending_items),
    }


def _source_snapshot(
    project: ProjectInput,
    tasks: tuple[LaunchTask, ...],
    budget_items: tuple[float, ...] | None,
) -> dict[str, Any]:
    return {
        "schema_version": "opening-rescue-v1",
        "project": _project_dict(project),
        "tasks": [
            {
                "task_id": task.task_id,
                "name": task.name,
                "duration_days": task.duration_days,
                "depends_on": list(task.depends_on),
                "category": task.category,
                "completed": task.completed,
            }
            for task in tasks
        ],
        "budget_items": list(budget_items) if budget_items is not None else None,
    }


def _scenario_from_mapping(payload: Mapping[str, Any]) -> RescueScenario:
    task_id = payload.get("task_id")
    if not isinstance(task_id, str) or not task_id or len(task_id) > 80:
        raise ValueError("INVALID_RESCUE_TASK")

    def whole_number(key: str, default: int | None = None) -> int:
        raw = payload.get(key, default)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"INVALID_{key.upper()}")
        number = float(raw)
        if not math.isfinite(number) or not number.is_integer():
            raise ValueError(f"INVALID_{key.upper()}")
        return int(number)

    raw_recovery_cost = payload.get("recovery_cost_per_day")
    recovery_cost = None if raw_recovery_cost is None else whole_number("recovery_cost_per_day")
    return RescueScenario(
        task_id=task_id,
        delay_workdays=whole_number("delay_workdays"),
        direct_budget_shock=whole_number("direct_budget_shock", 0),
        max_recoverable_workdays=whole_number("max_recoverable_workdays"),
        recovery_cost_per_day=recovery_cost,
    )


def _simulation_payload(simulation: Any) -> dict[str, Any]:
    return {
        "baseline_project_workdays": simulation.baseline_project_workdays,
        "scenario_project_workdays": simulation.scenario_project_workdays,
        "projected_delay_workdays": simulation.projected_delay_workdays,
        "scenario_opening_date": simulation.scenario_opening_date.isoformat(),
        "affected_task_ids": list(simulation.affected_task_ids),
        "timings": [
            {
                **asdict(item),
                "earliest_completion": item.earliest_completion.isoformat(),
                "latest_safe_completion": item.latest_safe_completion.isoformat(),
            }
            for item in simulation.timings
        ],
        "strategies": [
            {
                **asdict(item),
                "resulting_opening_date": item.resulting_opening_date.isoformat(),
                "blockers": list(item.blockers),
                "assumptions": list(item.assumptions),
            }
            for item in simulation.strategies
        ],
    }


def _decode_source_snapshot(
    value: Mapping[str, Any],
) -> tuple[ProjectInput, tuple[LaunchTask, ...], tuple[float, ...] | None]:
    if value.get("schema_version") != "opening-rescue-v1":
        raise ValueError("INVALID_RESCUE_SOURCE_VERSION")
    project_value = value.get("project")
    task_values = value.get("tasks")
    budget_values = value.get("budget_items")
    if not isinstance(project_value, dict) or not isinstance(task_values, list):
        raise ValueError("INVALID_RESCUE_SOURCE")
    project = parse_project_payload(project_value)
    tasks: list[LaunchTask] = []
    for item in task_values:
        if not isinstance(item, dict):
            raise ValueError("INVALID_RESCUE_SOURCE")
        depends_on = item.get("depends_on")
        if not isinstance(depends_on, list) or not all(
            isinstance(dependency, str) for dependency in depends_on
        ):
            raise ValueError("INVALID_RESCUE_SOURCE")
        try:
            task = LaunchTask(
                task_id=str(item["task_id"]),
                name=str(item["name"]),
                duration_days=int(item["duration_days"]),
                depends_on=tuple(depends_on),
                category=str(item["category"]),
                completed=bool(item["completed"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("INVALID_RESCUE_SOURCE") from exc
        tasks.append(task)
    budget_items = None
    if budget_values is not None:
        if not isinstance(budget_values, list):
            raise ValueError("INVALID_RESCUE_SOURCE")
        budget_items = _budget_items({"budget_items": budget_values})
    return project, tuple(tasks), budget_items


def recompute_rescue_from_snapshots(source_json: str, scenario_json: str) -> dict[str, Any]:
    """Independently reconstruct and recompute a scenario from canonical snapshots."""

    try:
        source_value = json.loads(source_json)
        scenario_value = json.loads(scenario_json)
    except json.JSONDecodeError as exc:
        raise ValueError("INVALID_RESCUE_SNAPSHOT") from exc
    if not isinstance(source_value, dict) or not isinstance(scenario_value, dict):
        raise ValueError("INVALID_RESCUE_SNAPSHOT")
    project, tasks, budget_items = _decode_source_snapshot(source_value)
    scenario = _scenario_from_mapping(scenario_value)
    normalized_source = _canonical_json(source_value)
    normalized_scenario = _canonical_json(asdict(scenario))
    result = _simulation_payload(simulate_opening_rescue(project, tasks, budget_items, scenario))
    result_json = _canonical_json(result)
    return {
        "result": result,
        "hashes": {
            "source": _digest(normalized_source),
            "shock": _digest(normalized_scenario),
            "result": _digest(result_json),
        },
    }


def _load_project_source(
    connection: sqlite3.Connection, project_id: str
) -> tuple[ProjectInput, tuple[LaunchTask, ...], tuple[float, ...] | None]:
    report = connection.execute(
        "SELECT content_json FROM readiness_report WHERE project_id = ? ORDER BY id DESC LIMIT 1",
        (project_id,),
    ).fetchone()
    if report is None:
        raise ValueError("PROJECT_NOT_FOUND")
    try:
        report_data = json.loads(str(report[0]))
    except json.JSONDecodeError as exc:
        raise ValueError("INVALID_BASELINE_REPORT") from exc
    project_data = report_data.get("project") if isinstance(report_data, dict) else None
    if not isinstance(project_data, dict):
        raise ValueError("INVALID_BASELINE_REPORT")
    project = parse_project_payload(project_data)
    task_rows = connection.execute(
        "SELECT id, name, duration_days, category, completed FROM launch_task "
        "WHERE project_id = ? ORDER BY rowid",
        (project_id,),
    ).fetchall()
    dependencies = connection.execute(
        "SELECT task_id, depends_on_task_id FROM task_dependency WHERE task_id IN "
        "(SELECT id FROM launch_task WHERE project_id = ?)",
        (project_id,),
    ).fetchall()
    prefix = f"{project_id}:"
    dependency_map: dict[str, list[str]] = {}
    for task_id, dependency_id in dependencies:
        dependency_map.setdefault(str(task_id), []).append(str(dependency_id).removeprefix(prefix))
    tasks = tuple(
        LaunchTask(
            task_id=str(row[0]).removeprefix(prefix),
            name=str(row[1]),
            duration_days=int(row[2]),
            depends_on=tuple(dependency_map.get(str(row[0]), ())),
            category=str(row[3]),
            completed=bool(row[4]),
        )
        for row in task_rows
    )
    budget_rows = connection.execute(
        "SELECT amount FROM budget_item WHERE project_id = ? ORDER BY id",
        (project_id,),
    ).fetchall()
    budget_items = tuple(float(row[0]) for row in budget_rows) or None
    return project, tasks, budget_items


def create_rescue_simulation(
    connection: sqlite3.Connection,
    project_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Persist an immutable deterministic rescue scenario without changing baseline state."""

    project, tasks, budget_items = _load_project_source(connection, project_id)
    scenario = _scenario_from_mapping(payload)
    source_json = _canonical_json(_source_snapshot(project, tasks, budget_items))
    scenario_json = _canonical_json(asdict(scenario))
    recomputed = recompute_rescue_from_snapshots(source_json, scenario_json)
    simulation_id = uuid4().hex
    output = {
        "simulation_id": simulation_id,
        "project_id": project_id,
        "status": "DETERMINISTIC_RESCUE_ONLY",
        "review_status": "LIVE_REVIEW_NOT_RUN",
        "scenario": asdict(scenario),
        **recomputed["result"],
        "hashes": recomputed["hashes"],
        "human_selection": {"status": "pending", "human_only": True},
    }
    with connection:
        connection.execute(
            "INSERT INTO rescue_simulation("
            "id, project_id, source_json, scenario_json, result_json, "
            "source_hash, shock_hash, result_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                simulation_id,
                project_id,
                source_json,
                scenario_json,
                _canonical_json(output),
                recomputed["hashes"]["source"],
                recomputed["hashes"]["shock"],
                recomputed["hashes"]["result"],
            ),
        )
        connection.execute(
            "INSERT INTO audit_event(project_id, event_type, detail) VALUES (?, ?, ?)",
            (project_id, "opening_rescue_simulated", f"simulation={simulation_id}"),
        )
    return output


def record_rescue_agent_review(
    connection: sqlite3.Connection,
    simulation_id: str,
    review: Mapping[str, Any],
) -> None:
    """Persist a read-only Agent review only when all deterministic hashes match."""

    row = connection.execute(
        "SELECT project_id, source_hash, shock_hash, result_hash "
        "FROM rescue_simulation WHERE id = ?",
        (simulation_id,),
    ).fetchone()
    if row is None:
        raise ValueError("RESCUE_SIMULATION_NOT_FOUND")
    hashes = review.get("hashes")
    expected = {"source": str(row[1]), "shock": str(row[2]), "result": str(row[3])}
    if (
        not isinstance(hashes, dict)
        or any(hashes.get(name) != value for name, value in expected.items())
        or review.get("hash_match") is not True
        or review.get("review_mode") != "independent-read-only"
    ):
        raise ValueError("RESCUE_HASH_MISMATCH")
    try:
        with connection:
            connection.execute(
                "INSERT INTO rescue_agent_review(simulation_id, result_json) VALUES (?, ?)",
                (simulation_id, _canonical_json(dict(review))),
            )
            connection.execute(
                "INSERT INTO audit_event(project_id, event_type, detail) VALUES (?, ?, ?)",
                (str(row[0]), "live_rescue_review_completed", f"simulation={simulation_id}"),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("RESCUE_REVIEW_ALREADY_RECORDED") from exc


def record_rescue_strategy(
    connection: sqlite3.Connection,
    simulation_id: str,
    strategy_id: str,
    actor: str = "demo_human",
) -> dict[str, str]:
    """Record one human strategy selection without applying it to the baseline project."""

    row = connection.execute(
        "SELECT project_id, result_json FROM rescue_simulation WHERE id = ?",
        (simulation_id,),
    ).fetchone()
    if row is None:
        raise ValueError("RESCUE_SIMULATION_NOT_FOUND")
    result = json.loads(str(row[1]))
    strategies = result.get("strategies") if isinstance(result, dict) else None
    selected = next(
        (
            item
            for item in strategies or ()
            if isinstance(item, dict) and item.get("strategy_id") == strategy_id
        ),
        None,
    )
    if selected is None:
        raise ValueError("INVALID_RESCUE_STRATEGY")
    if not selected.get("selectable"):
        raise ValueError("RESCUE_STRATEGY_BLOCKED")
    project_id = str(row[0])
    try:
        with connection:
            connection.execute(
                "INSERT INTO rescue_strategy_decision(simulation_id, strategy_id, actor) "
                "VALUES (?, ?, ?)",
                (simulation_id, strategy_id, actor),
            )
            connection.execute(
                "INSERT INTO audit_event(project_id, event_type, detail) VALUES (?, ?, ?)",
                (
                    project_id,
                    "human_rescue_strategy_selected",
                    f"simulation={simulation_id};strategy={strategy_id};actor={actor}",
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("RESCUE_STRATEGY_ALREADY_SELECTED") from exc
    return {
        "simulation_id": simulation_id,
        "strategy_id": strategy_id,
        "status": "recorded_not_applied",
    }


def apply_human_decision(
    connection: sqlite3.Connection,
    approval_id: int,
    decision: str,
    actor: str = "demo_human",
) -> str:
    """Record an explicit human decision; no agent can call this function."""

    if decision not in {"approved", "rejected", "deferred"}:
        raise ValueError("INVALID_HUMAN_DECISION")
    with connection:
        row = connection.execute(
            "UPDATE approval_request SET status = ? "
            "WHERE id = ? AND status = 'pending' RETURNING project_id",
            (decision, approval_id),
        ).fetchone()
        if row is None:
            exists = connection.execute(
                "SELECT 1 FROM approval_request WHERE id = ?", (approval_id,)
            ).fetchone()
            if exists is None:
                raise ValueError("APPROVAL_NOT_FOUND")
            raise ValueError("APPROVAL_ALREADY_DECIDED")
        project_id = row[0]
        connection.execute(
            "INSERT INTO human_decision(approval_id, decision) VALUES (?, ?)",
            (approval_id, decision),
        )
        connection.execute(
            "INSERT INTO audit_event(project_id, event_type, detail) VALUES (?, ?, ?)",
            (project_id, "human_decision_recorded", f"{decision};actor={actor}"),
        )
        report = connection.execute(
            "SELECT id, content_json FROM readiness_report WHERE project_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        if report is not None:
            content = json.loads(str(report[1]))
            if isinstance(content, dict):
                approval = content.get("approval_request")
                if isinstance(approval, dict):
                    approval["status"] = decision
                content["human_decision"] = {"decision": decision}
                connection.execute(
                    "UPDATE readiness_report SET content_json = ? WHERE id = ?",
                    (json.dumps(content, ensure_ascii=False), report[0]),
                )
    return decision


def demo_payload() -> dict[str, Any]:
    return {
        "store_type": "街邊咖啡店",
        "location": "台北市大安區（虛構示例）",
        "budget": 800_000,
        "opening_date": "2026-10-30",
        "acquired_documents": ["店面租約與餐飲用途同意文件", "商業登記申請資料"],
        "missing_documents": [
            "建物使用與營業場所證明",
            "消防安全設備檢查資料",
            "食品業者登錄準備資料",
            "排煙與油脂截留設備確認資料",
        ],
        "completed_items": ["確認租約與餐飲用途", "完成登記、場所與消防文件盤點"],
        "pending_items": [
            "確認用電、給排水與排煙容量",
            "完成廚房、吧台與顧客動線工程",
            "完成冷藏、製作與收銀設備測試",
            "完成供應商、食材規格與首批備料",
            "完成菜單、定價與食品保存流程",
            "完成招募、排班與職責配置",
            "完成食品安全與服務訓練",
            "完成清潔、試營運與開幕演練",
        ],
        "budget_items": [330_000, 240_000, 100_000, 65_000],
    }
