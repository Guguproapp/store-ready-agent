"""Small SQLite persistence layer for the MVP."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from .domain import LaunchTask, ProjectInput

SCHEMA = """
CREATE TABLE IF NOT EXISTS project (
  id TEXT PRIMARY KEY,
  store_type TEXT NOT NULL,
  location TEXT NOT NULL,
  budget REAL NOT NULL,
  opening_date TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS launch_task (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project(id),
  name TEXT NOT NULL,
  duration_days INTEGER NOT NULL,
  category TEXT NOT NULL,
  completed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS task_dependency (
  task_id TEXT NOT NULL REFERENCES launch_task(id),
  depends_on_task_id TEXT NOT NULL REFERENCES launch_task(id),
  PRIMARY KEY (task_id, depends_on_task_id)
);
CREATE TABLE IF NOT EXISTS document_requirement (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES project(id),
  name TEXT NOT NULL,
  status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS budget_item (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES project(id),
  name TEXT NOT NULL,
  amount REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS risk_finding (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES project(id),
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  detail TEXT NOT NULL,
  severity TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approval_request (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES project(id),
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS human_decision (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  approval_id INTEGER NOT NULL REFERENCES approval_request(id),
  decision TEXT NOT NULL,
  decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES project(id),
  event_type TEXT NOT NULL,
  detail TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS readiness_report (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES project(id),
  source TEXT NOT NULL,
  score INTEGER NOT NULL,
  content_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rescue_simulation (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES project(id),
  source_json TEXT NOT NULL,
  scenario_json TEXT NOT NULL,
  result_json TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  shock_hash TEXT NOT NULL,
  result_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rescue_strategy_decision (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  simulation_id TEXT NOT NULL UNIQUE REFERENCES rescue_simulation(id),
  strategy_id TEXT NOT NULL,
  actor TEXT NOT NULL,
  decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS rescue_agent_review (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  simulation_id TEXT NOT NULL UNIQUE REFERENCES rescue_simulation(id),
  result_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection


def seed_project(
    connection: sqlite3.Connection,
    project_id: str,
    project: ProjectInput,
    tasks: Iterable[LaunchTask],
) -> None:
    """Persist a project and its task/dependency rows; callers own validation."""

    connection.execute(
        "INSERT INTO project(id, store_type, location, budget, opening_date) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            project_id,
            project.store_type,
            project.location,
            project.budget,
            project.opening_date.isoformat(),
        ),
    )
    for task in tasks:
        stored_task_id = f"{project_id}:{task.task_id}"
        connection.execute(
            "INSERT INTO launch_task(id, project_id, name, duration_days, category, completed) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                stored_task_id,
                project_id,
                task.name,
                task.duration_days,
                task.category,
                int(task.completed),
            ),
        )
        connection.executemany(
            "INSERT INTO task_dependency(task_id, depends_on_task_id) VALUES (?, ?)",
            ((stored_task_id, f"{project_id}:{dependency}") for dependency in task.depends_on),
        )
    connection.commit()


def prune_demo_projects(
    connection: sqlite3.Connection,
    *,
    retain: int = 499,
    ttl_hours: int = 2,
) -> tuple[str, ...]:
    """Delete expired/oldest fictional projects and every dependent row."""

    if retain < 0 or ttl_hours < 1:
        raise ValueError("INVALID_DEMO_RETENTION")
    expired = {
        str(row[0])
        for row in connection.execute(
            "SELECT id FROM project WHERE created_at < datetime('now', ?)",
            (f"-{ttl_hours} hours",),
        )
    }
    ordered = [
        str(row[0])
        for row in connection.execute("SELECT id FROM project ORDER BY created_at, id")
        if str(row[0]) not in expired
    ]
    excess = max(0, len(ordered) - retain)
    targets = tuple(sorted(expired | set(ordered[:excess])))
    with connection:
        for project_id in targets:
            connection.execute(
                "DELETE FROM rescue_strategy_decision WHERE simulation_id IN "
                "(SELECT id FROM rescue_simulation WHERE project_id = ?)",
                (project_id,),
            )
            connection.execute(
                "DELETE FROM rescue_agent_review WHERE simulation_id IN "
                "(SELECT id FROM rescue_simulation WHERE project_id = ?)",
                (project_id,),
            )
            connection.execute(
                "DELETE FROM human_decision WHERE approval_id IN "
                "(SELECT id FROM approval_request WHERE project_id = ?)",
                (project_id,),
            )
            connection.execute(
                "DELETE FROM task_dependency WHERE task_id IN "
                "(SELECT id FROM launch_task WHERE project_id = ?) "
                "OR depends_on_task_id IN "
                "(SELECT id FROM launch_task WHERE project_id = ?)",
                (project_id, project_id),
            )
            for table in (
                "document_requirement",
                "budget_item",
                "risk_finding",
                "approval_request",
                "audit_event",
                "readiness_report",
                "rescue_simulation",
                "launch_task",
            ):
                connection.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))
            connection.execute("DELETE FROM project WHERE id = ?", (project_id,))
    return targets
