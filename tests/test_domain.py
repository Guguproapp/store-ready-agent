import unittest
from datetime import date

from store_ready.domain import (
    LaunchTask,
    ProjectInput,
    calculate_critical_path,
    calculate_readiness,
    detect_readiness_gaps,
)


class DomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = ProjectInput(
            "咖啡店", "虛構地點", 100, date(2026, 10, 30), ("租約",), ("消防",)
        )
        self.tasks = (
            LaunchTask("a", "A", 2),
            LaunchTask("b", "B", 2, ("a",)),
            LaunchTask("c", "C", 1, ("a",)),
        )

    def test_critical_path_is_deterministic(self) -> None:
        schedules = calculate_critical_path(self.tasks, self.project.opening_date)
        by_id = {item.task_id: item for item in schedules}
        self.assertEqual(by_id["b"].due_date, self.project.opening_date)
        self.assertLessEqual(by_id["a"].due_date, by_id["b"].start_date)
        self.assertEqual(
            {item.task_id for item in schedules if item.critical},
            {"a", "b"},
        )

    def test_deadline_scheduling_skips_weekends(self) -> None:
        tasks = (LaunchTask("a", "A", 2), LaunchTask("b", "B", 1, ("a",)))
        schedules = {
            item.task_id: item for item in calculate_critical_path(tasks, date(2026, 11, 2))
        }
        self.assertEqual(schedules["b"].start_date, date(2026, 11, 2))
        self.assertEqual(schedules["a"].due_date, date(2026, 10, 30))
        self.assertEqual(schedules["a"].start_date, date(2026, 10, 29))

    def test_multiple_equal_terminal_paths_are_all_critical(self) -> None:
        tasks = (
            LaunchTask("a", "A", 2),
            LaunchTask("b", "B", 2, ("a",)),
            LaunchTask("c", "C", 2),
            LaunchTask("d", "D", 2, ("c",)),
        )
        schedules = calculate_critical_path(tasks, self.project.opening_date)
        self.assertEqual(
            {item.task_id for item in schedules if item.critical},
            {"a", "b", "c", "d"},
        )

    def test_unknown_dependency_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "UNKNOWN_TASK_DEPENDENCY"):
            calculate_critical_path((LaunchTask("a", "A", 1, ("missing",)),), date(2026, 10, 30))

    def test_cycle_is_rejected(self) -> None:
        tasks = (LaunchTask("a", "A", 1, ("b",)), LaunchTask("b", "B", 1, ("a",)))
        with self.assertRaisesRegex(ValueError, "TASK_DEPENDENCY_CYCLE"):
            calculate_critical_path(tasks, self.project.opening_date)

    def test_invalid_duration_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "INVALID_TASK_DURATION"):
            calculate_critical_path((LaunchTask("a", "A", 0),), self.project.opening_date)

    def test_gaps_include_document_and_budget(self) -> None:
        gaps = detect_readiness_gaps(self.project, self.tasks, (80, 40))
        self.assertEqual({gap.kind for gap in gaps}, {"document", "budget"})

    def test_score_is_bounded(self) -> None:
        result = calculate_readiness(self.project, self.tasks, (80, 40))
        self.assertGreaterEqual(result.score, 0)
        self.assertLessEqual(result.score, 100)

    def test_delay_forecast_uses_unfinished_critical_start_and_as_of_date(self) -> None:
        tasks = (
            LaunchTask("a", "A", 2, completed=True),
            LaunchTask("b", "B", 3, ("a",)),
        )
        result = calculate_readiness(
            self.project,
            tasks,
            (80, 20),
            as_of_date=date(2026, 10, 30),
        )
        self.assertEqual(result.delayed_days, 2)


if __name__ == "__main__":
    unittest.main()
