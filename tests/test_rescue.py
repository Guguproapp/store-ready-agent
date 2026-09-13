import json
import os
import unittest
from dataclasses import replace
from datetime import date
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

from store_ready.agents import (
    LiveEvidence,
    LivePreflightFailed,
    _check_rescue_required_calls,
    _independent_rescue_review,
    evidence_document,
)
from store_ready.domain import (
    RescueScenario,
    calculate_task_timing,
    default_tasks,
    demo_project,
    simulate_opening_rescue,
)
from store_ready.service import (
    analyze_payload,
    create_rescue_simulation,
    demo_payload,
    recompute_rescue_from_snapshots,
    record_rescue_strategy,
)
from store_ready.storage import connect
from store_ready.web_app import HTML, JAVASCRIPT, STYLESHEET, Handler


class RescueDomainTests(unittest.TestCase):
    def test_task_timing_exposes_last_safe_date_and_branch_slack(self) -> None:
        project = demo_project()
        timing = {
            item.task_id: item
            for item in calculate_task_timing(default_tasks(project), project.opening_date)
        }

        self.assertEqual(timing["fitout"].slack_workdays, 0)
        self.assertTrue(timing["fitout"].critical)
        self.assertEqual(timing["permits"].slack_workdays, 4)
        self.assertFalse(timing["permits"].critical)
        self.assertLess(
            timing["permits"].earliest_completion, timing["permits"].latest_safe_completion
        )

    def test_critical_and_noncritical_shocks_propagate_deterministically(self) -> None:
        project = replace(demo_project(), completed_items=("確認租約與餐飲用途",))
        tasks = default_tasks(project)
        critical = simulate_opening_rescue(
            project,
            tasks,
            (330_000, 240_000, 100_000, 65_000),
            RescueScenario("fitout", 4, 50_000, 4, 5_000),
        )
        absorbed = simulate_opening_rescue(
            project,
            tasks,
            (330_000, 240_000, 100_000, 65_000),
            RescueScenario("permits", 4, 0, 0, 0),
        )
        exceeded = simulate_opening_rescue(
            project,
            tasks,
            (330_000, 240_000, 100_000, 65_000),
            RescueScenario("permits", 5, 0, 0, 0),
        )

        self.assertEqual(critical.projected_delay_workdays, 4)
        self.assertIn("inspection", critical.affected_task_ids)
        self.assertEqual(absorbed.projected_delay_workdays, 0)
        self.assertEqual(exceeded.projected_delay_workdays, 1)

    def test_three_strategies_use_fixed_date_and_budget_formulas(self) -> None:
        result = simulate_opening_rescue(
            demo_project(),
            default_tasks(demo_project()),
            (330_000, 240_000, 100_000, 65_000),
            RescueScenario("fitout", 4, 50_000, 4, 5_000),
        )
        strategies = {item.strategy_id: item for item in result.strategies}

        self.assertEqual(tuple(strategies), ("protect_date", "protect_budget", "lowest_risk"))
        self.assertEqual(strategies["protect_date"].recovered_workdays, 4)
        self.assertEqual(strategies["protect_date"].residual_delay_workdays, 0)
        self.assertEqual(strategies["protect_date"].budget_total, 805_000)
        self.assertEqual(strategies["protect_date"].resulting_opening_date, date(2026, 10, 30))
        self.assertEqual(strategies["protect_budget"].resulting_opening_date, date(2026, 11, 5))
        self.assertEqual(strategies["protect_budget"].budget_total, 785_000)
        self.assertEqual(strategies["lowest_risk"].recovered_workdays, 3)
        self.assertEqual(strategies["lowest_risk"].residual_delay_workdays, 1)
        self.assertEqual(strategies["lowest_risk"].budget_total, 800_000)
        self.assertEqual(strategies["lowest_risk"].resulting_opening_date, date(2026, 11, 2))

    def test_unknown_budget_and_quote_block_unsafe_choices(self) -> None:
        result = simulate_opening_rescue(
            demo_project(),
            default_tasks(demo_project()),
            None,
            RescueScenario("fitout", 3, 0, 3, None),
        )
        self.assertTrue(all(not item.selectable for item in result.strategies))
        self.assertTrue(all(item.budget_total is None for item in result.strategies))
        self.assertIn("BUDGET_DETAILS_REQUIRED", result.strategies[0].blockers)

    def test_invalid_or_completed_shock_fails_closed(self) -> None:
        project = demo_project()
        tasks = default_tasks(project)
        invalid = (
            RescueScenario("unknown", 2, 0, 1, 1),
            RescueScenario("fitout", 0, 0, 1, 1),
            RescueScenario("fitout", 61, 0, 1, 1),
            RescueScenario("fitout", 2, -1, 1, 1),
        )
        for scenario in invalid:
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                simulate_opening_rescue(project, tasks, (), scenario)

        completed_tasks = tuple(
            replace(item, completed=True) if item.task_id == "fitout" else item for item in tasks
        )
        with self.assertRaisesRegex(ValueError, "COMPLETED_TASK_CANNOT_BE_SHOCKED"):
            simulate_opening_rescue(
                project,
                completed_tasks,
                (),
                RescueScenario("fitout", 2, 0, 1, 1),
            )


class RescueServiceTests(unittest.TestCase):
    def test_simulation_is_immutable_hashed_and_selection_is_one_shot(self) -> None:
        connection = connect()
        baseline = analyze_payload(demo_payload(), connection)
        original_report = connection.execute(
            "SELECT content_json FROM readiness_report WHERE project_id = ?",
            (baseline["project_id"],),
        ).fetchone()[0]
        simulation = create_rescue_simulation(
            connection,
            baseline["project_id"],
            {
                "task_id": "fitout",
                "delay_workdays": 4,
                "direct_budget_shock": 50_000,
                "max_recoverable_workdays": 4,
                "recovery_cost_per_day": 5_000,
            },
        )

        self.assertEqual(simulation["status"], "DETERMINISTIC_RESCUE_ONLY")
        self.assertEqual(simulation["review_status"], "LIVE_REVIEW_NOT_RUN")
        self.assertEqual(len(simulation["strategies"]), 3)
        self.assertTrue(all(len(value) == 64 for value in simulation["hashes"].values()))
        row = connection.execute(
            "SELECT source_json, scenario_json, result_hash FROM rescue_simulation WHERE id = ?",
            (simulation["simulation_id"],),
        ).fetchone()
        recomputed = recompute_rescue_from_snapshots(row[0], row[1])
        self.assertEqual(recomputed["hashes"]["result"], row[2])

        decision = record_rescue_strategy(
            connection,
            simulation["simulation_id"],
            "protect_budget",
            actor="demo_browser_session",
        )
        self.assertEqual(decision["strategy_id"], "protect_budget")
        self.assertEqual(
            connection.execute(
                "SELECT content_json FROM readiness_report WHERE project_id = ?",
                (baseline["project_id"],),
            ).fetchone()[0],
            original_report,
        )
        with self.assertRaisesRegex(ValueError, "RESCUE_STRATEGY_ALREADY_SELECTED"):
            record_rescue_strategy(
                connection,
                simulation["simulation_id"],
                "protect_date",
            )

    def test_snapshot_tampering_changes_server_recomputed_hash(self) -> None:
        connection = connect()
        baseline = analyze_payload(demo_payload(), connection)
        simulation = create_rescue_simulation(
            connection,
            baseline["project_id"],
            {
                "task_id": "fitout",
                "delay_workdays": 4,
                "direct_budget_shock": 50_000,
                "max_recoverable_workdays": 4,
                "recovery_cost_per_day": 5_000,
            },
        )
        row = connection.execute(
            "SELECT source_json, scenario_json FROM rescue_simulation WHERE id = ?",
            (simulation["simulation_id"],),
        ).fetchone()
        tampered = json.loads(row[1])
        tampered["delay_workdays"] = 8
        recomputed = recompute_rescue_from_snapshots(
            row[0], json.dumps(tampered, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        self.assertNotEqual(recomputed["hashes"]["result"], simulation["hashes"]["result"])

    def test_reviewer_ignores_manager_output_and_hash_mismatch_fails_closed(self) -> None:
        connection = connect()
        baseline = analyze_payload(demo_payload(), connection)
        simulation = create_rescue_simulation(
            connection,
            baseline["project_id"],
            {
                "task_id": "fitout",
                "delay_workdays": 4,
                "direct_budget_shock": 50_000,
                "max_recoverable_workdays": 4,
                "recovery_cost_per_day": 5_000,
            },
        )
        row = connection.execute(
            "SELECT source_json, scenario_json FROM rescue_simulation WHERE id = ?",
            (simulation["simulation_id"],),
        ).fetchone()
        reviewed = _independent_rescue_review(
            row[0],
            row[1],
            simulation["hashes"],
            untrusted_manager_output={"projected_delay_workdays": 0},
        )
        self.assertEqual(reviewed["projected_delay_workdays"], 4)
        self.assertEqual(reviewed["review_mode"], "independent-read-only")
        with self.assertRaisesRegex(LivePreflightFailed, "RESCUE_HASH_MISMATCH"):
            _independent_rescue_review(
                row[0],
                row[1],
                {**simulation["hashes"], "result": "0" * 64},
            )

    def test_rescue_live_evidence_requires_both_agents_and_simulator_tools(self) -> None:
        evidence = LiveEvidence(
            manager_agent_id="launch-manager-rescue-live",
            reviewer_agent_id="readiness-reviewer-rescue-live",
        )
        for agent, tool in (
            ("launch_manager", "simulate_opening_rescue"),
            ("launch_manager", "readiness_reviewer"),
            ("readiness_reviewer", "simulate_opening_rescue"),
            ("readiness_reviewer", "verify_rescue_hashes"),
            ("readiness_reviewer", "generate_rescue_review"),
        ):
            evidence.record(agent, tool, f"{agent}-{tool}", "success", 1, "a" * 64)
        _check_rescue_required_calls(evidence)
        evidence.tool_calls.pop()
        with self.assertRaisesRegex(LivePreflightFailed, "RESCUE_TOOL_CALLS_INCOMPLETE"):
            _check_rescue_required_calls(evidence)


class RescueEvidenceTests(unittest.TestCase):
    def test_evidence_reports_the_limits_actually_enforced(self) -> None:
        evidence = LiveEvidence(manager_cycle_limit=4, reviewer_cycle_limit=6)
        document = evidence_document(evidence)

        self.assertEqual(document["limits"]["manager_cycles"], 4)
        self.assertEqual(document["limits"]["reviewer_cycles"], 6)
        self.assertIn("tests/test_rescue.py", document["source_files"])


class RescueWebTests(unittest.TestCase):
    def test_rescue_ui_exposes_accessible_human_only_flow(self) -> None:
        self.assertIn("開幕延誤模擬", HTML)
        self.assertIn('id="rescue-form"', HTML)
        self.assertIn('role="radiogroup"', HTML)
        self.assertIn('id="rescue-dialog"', HTML)
        self.assertIn("同一情境只能記錄一次", JAVASCRIPT)
        self.assertIn("原計畫、日期與預算都沒有變更", JAVASCRIPT)
        self.assertIn("計算核對完成", JAVASCRIPT)
        self.assertIn("grid-template-columns: repeat(3,minmax(0,1fr))", STYLESHEET)
        self.assertNotIn("innerHTML", HTML + JAVASCRIPT)

    def test_project_brief_is_guided_and_product_copy_is_clean(self) -> None:
        self.assertIn('name="store_type"', HTML)
        self.assertIn('name="location_city"', HTML)
        self.assertIn('name="location_area"', HTML)
        self.assertIn('name="budget_range"', HTML)
        self.assertIn('data-document-slot="0"', HTML)
        self.assertIn('data-task-slot="0"', HTML)
        for city_or_county in (
            "基隆市",
            "台北市",
            "新北市",
            "桃園市",
            "新竹市",
            "新竹縣",
            "苗栗縣",
            "台中市",
            "彰化縣",
            "南投縣",
            "雲林縣",
            "嘉義市",
            "嘉義縣",
            "台南市",
            "高雄市",
            "屏東縣",
            "宜蘭縣",
            "花蓮縣",
            "台東縣",
            "澎湖縣",
            "金門縣",
            "連江縣",
        ):
            self.assertIn(city_or_county, HTML)
        self.assertNotIn('<textarea name="acquired_documents"', HTML)
        self.assertNotIn('<textarea name="missing_documents"', HTML)
        self.assertNotIn('<textarea name="completed_items"', HTML)
        self.assertNotIn('<textarea name="pending_items"', HTML)
        for temporary_copy in ("測試環境", "公開測試版", "真人", "DEMO ·"):
            self.assertNotIn(temporary_copy, HTML + JAVASCRIPT)

    def test_homepage_is_chinese_and_store_type_focused(self) -> None:
        self.assertIn('id="index-overview"', HTML)
        self.assertIn("開店就緒助手", HTML)
        self.assertIn("開幕前先看清楚三個關鍵問題", HTML)
        self.assertIn("開始檢查開幕風險", HTML)
        self.assertIn('id="focus-summary"', HTML)
        self.assertEqual(HTML.count("data-document-slot="), 8)
        self.assertEqual(HTML.count("data-task-slot="), 10)
        self.assertIn("focusPresets", JAVASCRIPT)
        self.assertIn("食品業者登錄相關資料", JAVASCRIPT)
        self.assertIn("確認用電、給排水與排煙容量", JAVASCRIPT)
        self.assertIn("完成清潔、試營運與開幕演練", JAVASCRIPT)
        self.assertIn("applyFocusPreset", JAVASCRIPT)

        for english_copy in (
            "StoreReady",
            "Launch Manager",
            "Readiness Reviewer",
            "PROJECT BRIEF",
            "AGENT RUN",
            "READY WHEN YOU ARE",
            "READINESS OVERVIEW",
            "RISK CONTROL",
            "CRITICAL PATH",
            "OPENING RESCUE SIMULATOR",
            "SIGNATURE FEATURE",
            "DUAL-AGENT REVIEW",
            "YOUR DECISION",
            "EXPORT & AUDIT",
            "Audit Log",
        ):
            self.assertNotIn(english_copy, HTML + JAVASCRIPT)

    def test_public_live_rescue_is_disabled_before_agent_boundary(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/live-rescue/fictional-project",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with (
                patch.dict("os.environ", {}, clear=True),
                patch("store_ready.web_app.run_live_rescue_review") as live_boundary,
                self.assertRaises(HTTPError) as error,
            ):
                urlopen(request)
            self.assertEqual(error.exception.code, 503)
            live_boundary.assert_not_called()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_rescue_and_human_selection_are_session_bound_and_one_shot(self) -> None:
        previous_cwd = os.getcwd()
        with TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            first = build_opener(HTTPCookieProcessor(CookieJar()))
            second = build_opener(HTTPCookieProcessor(CookieJar()))

            def read_json(opener: object, request: Request) -> dict[str, object]:
                with opener.open(request) as response:  # type: ignore[attr-defined]
                    return json.loads(response.read())  # type: ignore[no-any-return]

            try:
                first_session = read_json(first, Request(base_url + "/api/session"))
                first_csrf = str(first_session["csrf_token"])
                analyze = read_json(
                    first,
                    Request(
                        base_url + "/api/analyze",
                        data=json.dumps(demo_payload()).encode(),
                        headers={
                            "Content-Type": "application/json",
                            "X-CSRF-Token": first_csrf,
                        },
                        method="POST",
                    ),
                )
                project_id = str(analyze["project_id"])
                scenario_body = json.dumps(
                    {
                        "task_id": "fitout",
                        "delay_workdays": 4,
                        "direct_budget_shock": 50_000,
                        "max_recoverable_workdays": 4,
                        "recovery_cost_per_day": 5_000,
                    }
                ).encode()
                rescue_url = base_url + f"/api/rescue/{project_id}"
                rescue = read_json(
                    first,
                    Request(
                        rescue_url,
                        data=scenario_body,
                        headers={
                            "Content-Type": "application/json",
                            "X-CSRF-Token": first_csrf,
                        },
                        method="POST",
                    ),
                )
                self.assertEqual(len(rescue["strategies"]), 3)  # type: ignore[arg-type]
                simulation_id = str(rescue["simulation_id"])

                second_session = read_json(second, Request(base_url + "/api/session"))
                with self.assertRaises(HTTPError) as cross_session:
                    second.open(
                        Request(
                            rescue_url,
                            data=scenario_body,
                            headers={
                                "Content-Type": "application/json",
                                "X-CSRF-Token": str(second_session["csrf_token"]),
                            },
                            method="POST",
                        )
                    )
                self.assertEqual(cross_session.exception.code, 403)

                decision_url = base_url + f"/api/rescue-decision/{simulation_id}"
                decision_request = Request(
                    decision_url,
                    data=json.dumps({"strategy_id": "protect_budget"}).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "X-CSRF-Token": first_csrf,
                    },
                    method="POST",
                )
                decision = read_json(first, decision_request)
                self.assertEqual(decision["status"], "recorded_not_applied")
                with self.assertRaises(HTTPError) as repeated:
                    first.open(decision_request)
                self.assertEqual(repeated.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
