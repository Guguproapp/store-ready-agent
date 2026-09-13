import json
import unittest
from math import inf, nan

from store_ready.service import analyze_payload, apply_human_decision, demo_payload
from store_ready.storage import connect


class ServiceTests(unittest.TestCase):
    def test_demo_analysis_is_explicitly_non_ai(self) -> None:
        result = analyze_payload(demo_payload())
        self.assertEqual(result["status"], "DETERMINISTIC_DEMO_ONLY")
        self.assertEqual(result["approval_request"]["human_only"], True)
        self.assertIn("完成食品安全與服務訓練", result["project"]["pending_items"])
        self.assertEqual(len(result["schedule"]), 10)
        self.assertEqual(
            result["critical_path"],
            ["lease", "fitout", "staffing", "training", "inspection"],
        )
        training = next(item for item in result["schedule"] if item["task_id"] == "training")
        self.assertEqual(training["depends_on"], ["staffing"])
        self.assertEqual(training["depends_on_names"], ["完成招募、排班與職責配置"])
        self.assertEqual(training["status"], "pending")

    def test_analysis_persists_audit_and_report(self) -> None:
        connection = connect()
        result = analyze_payload(demo_payload(), connection)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM audit_event").fetchone()[0], 1)
        self.assertTrue(result["report_available"])
        self.assertEqual(
            connection.execute("SELECT COUNT(*) FROM readiness_report").fetchone()[0], 1
        )
        self.assertEqual(
            connection.execute("SELECT status FROM approval_request").fetchone()[0], "pending"
        )
        self.assertEqual(
            connection.execute("SELECT detail FROM audit_event").fetchone()[0],
            "deterministic tools completed",
        )

    def test_invalid_input_is_rejected(self) -> None:
        payload = demo_payload()
        payload["budget"] = 0
        with self.assertRaisesRegex(ValueError, "INVALID_BUDGET"):
            analyze_payload(payload)

    def test_locations_outside_taiwan_are_rejected(self) -> None:
        for location in ("Tokyo, Japan", "New York, United States", "虛構地點"):
            payload = demo_payload()
            payload["location"] = location
            with self.subTest(location=location):
                with self.assertRaisesRegex(ValueError, "LOCATION_OUTSIDE_TAIWAN"):
                    analyze_payload(payload)

    def test_chinese_and_english_taiwan_locations_are_accepted(self) -> None:
        for location in ("臺中市西區（虛構示例）", "Taipei City / Residential commercial area"):
            payload = demo_payload()
            payload["location"] = location
            with self.subTest(location=location):
                self.assertEqual(analyze_payload(payload)["project"]["location"], location)

    def test_input_limits_and_non_finite_numbers_are_rejected(self) -> None:
        cases = []
        payload = demo_payload()
        payload["store_type"] = "店" * 81
        cases.append(payload)
        payload = demo_payload()
        payload["location"] = "地" * 161
        cases.append(payload)
        payload = demo_payload()
        payload["missing_documents"] = ["文件"] * 51
        cases.append(payload)
        payload = demo_payload()
        payload["completed_items"] = ["項" * 161]
        cases.append(payload)
        for invalid_budget in (nan, inf, -1, 1_000_000_000_001):
            payload = demo_payload()
            payload["budget"] = invalid_budget
            cases.append(payload)
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    analyze_payload(payload)

    def test_contradictory_lists_are_rejected(self) -> None:
        payload = demo_payload()
        payload["acquired_documents"] = ["消防資料"]
        payload["missing_documents"] = ["消防資料"]
        with self.assertRaisesRegex(ValueError, "CONTRADICTORY_DOCUMENT_STATUS"):
            analyze_payload(payload)

    def test_budget_items_must_be_finite_and_bounded(self) -> None:
        for items in ([nan], [inf], [1] * 51, [1e308] * 50):
            payload = demo_payload()
            payload["budget_items"] = items
            with self.subTest(items=items):
                with self.assertRaisesRegex(ValueError, "INVALID_BUDGET_ITEMS"):
                    analyze_payload(payload)

    def test_missing_budget_details_are_reported_without_invented_amounts(self) -> None:
        payload = demo_payload()
        payload.pop("budget_items")
        result = analyze_payload(payload)
        self.assertEqual(result["budget_data_status"], "insufficient")
        self.assertEqual(result["score_status"], "provisional")
        self.assertEqual(result["score"], 30)
        self.assertIsNone(result["budget_total"])
        self.assertIsNone(result["budget_overage"])
        self.assertIsNone(result["budget_remaining"])
        self.assertIn("預算明細不足", {item["title"] for item in result["gaps"]})
        self.assertNotIn("預算超支", {item["title"] for item in result["gaps"]})

    def test_opening_date_is_bounded_before_scheduling(self) -> None:
        for opening_date in ("0001-01-01", "1999-12-31", "2101-01-01", "9999-12-31"):
            payload = demo_payload()
            payload["opening_date"] = opening_date
            with self.subTest(opening_date=opening_date):
                with self.assertRaisesRegex(ValueError, "INVALID_OPENING_DATE"):
                    analyze_payload(payload)

    def test_unknown_pending_item_is_not_silently_ignored(self) -> None:
        payload = demo_payload()
        payload["pending_items"] = ["等待房東提供未排程的門牌證明"]
        result = analyze_payload(payload)
        self.assertEqual(result["unmapped_pending_items"], ["等待房東提供未排程的門牌證明"])
        gap = next(item for item in result["gaps"] if item["title"] == "待辦尚未排程")
        self.assertIn("等待房東", gap["detail"])

    def test_human_decision_is_explicit_and_one_shot(self) -> None:
        connection = connect()
        result = analyze_payload(demo_payload(), connection)
        approval_id = result["approval_request"]["id"]
        self.assertEqual(apply_human_decision(connection, approval_id, "deferred"), "deferred")
        self.assertEqual(
            connection.execute("SELECT status FROM approval_request").fetchone()[0], "deferred"
        )
        report = json.loads(
            connection.execute(
                "SELECT content_json FROM readiness_report ORDER BY id DESC LIMIT 1"
            ).fetchone()[0]
        )
        self.assertEqual(report["approval_request"]["status"], "deferred")
        self.assertEqual(report["human_decision"]["decision"], "deferred")
        self.assertIn(
            "actor=demo_human",
            connection.execute(
                "SELECT detail FROM audit_event WHERE event_type = 'human_decision_recorded'"
            ).fetchone()[0],
        )
        with self.assertRaisesRegex(ValueError, "APPROVAL_ALREADY_DECIDED"):
            apply_human_decision(connection, approval_id, "approved")


if __name__ == "__main__":
    unittest.main()
