import unittest

from store_ready.domain import default_tasks, demo_project
from store_ready.service import analyze_payload, demo_payload
from store_ready.storage import connect, prune_demo_projects, seed_project


class StorageTests(unittest.TestCase):
    def test_sqlite_schema_rebuilds(self) -> None:
        connection = connect()
        project = demo_project()
        tasks = default_tasks(project)
        seed_project(connection, "demo-1", project, tasks)
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        self.assertTrue(
            {"project", "launch_task", "task_dependency", "audit_event", "readiness_report"}
            <= tables
        )
        self.assertEqual(
            connection.execute("SELECT COUNT(*) FROM launch_task").fetchone()[0], len(tasks)
        )

    def test_task_ids_are_isolated_between_projects(self) -> None:
        connection = connect()
        analyze_payload(demo_payload(), connection)
        analyze_payload(demo_payload(), connection)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM project").fetchone()[0], 2)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM launch_task").fetchone()[0], 20)

    def test_demo_project_retention_removes_expired_and_excess_rows(self) -> None:
        connection = connect()
        first = analyze_payload(demo_payload(), connection)["project_id"]
        second = analyze_payload(demo_payload(), connection)["project_id"]
        connection.execute(
            "UPDATE project SET created_at = datetime('now', '-3 hours') WHERE id = ?",
            (first,),
        )
        connection.execute(
            "UPDATE project SET created_at = datetime('now', '-30 minutes') WHERE id = ?",
            (second,),
        )
        connection.commit()
        self.assertEqual(prune_demo_projects(connection, retain=10, ttl_hours=2), (first,))
        self.assertEqual(
            connection.execute(
                "SELECT COUNT(*) FROM launch_task WHERE project_id = ?", (first,)
            ).fetchone()[0],
            0,
        )

        third = analyze_payload(demo_payload(), connection)["project_id"]
        connection.execute(
            "UPDATE project SET created_at = datetime('now', '-20 minutes') WHERE id = ?",
            (third,),
        )
        connection.commit()
        self.assertEqual(prune_demo_projects(connection, retain=1, ttl_hours=2), (second,))
        self.assertEqual({row[0] for row in connection.execute("SELECT id FROM project")}, {third})
        for table in (
            "launch_task",
            "document_requirement",
            "budget_item",
            "risk_finding",
            "approval_request",
            "audit_event",
            "readiness_report",
        ):
            with self.subTest(table=table):
                self.assertEqual(
                    connection.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE project_id = ?", (second,)
                    ).fetchone()[0],
                    0,
                )


if __name__ == "__main__":
    unittest.main()
