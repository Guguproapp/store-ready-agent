import json
import os
import unittest
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from tempfile import TemporaryDirectory
from threading import Thread
from typing import cast
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

from store_ready.web_app import (
    HTML,
    JAVASCRIPT,
    MAX_ANALYSES_PER_MINUTE,
    MAX_ANALYSES_PER_SESSION,
    SESSION_TTL_SECONDS,
    STYLESHEET,
    DemoLimitExceeded,
    Handler,
    _approval_belongs_to_session,
    _approval_owners,
    _bind_approval,
    _bind_project,
    _demo_sessions,
    _new_demo_session,
    _project_belongs_to_session,
    _project_owners,
    _reserve_analysis,
    _session_csrf,
    _session_lock,
    live_endpoint_enabled,
)


class WebSurfaceTests(unittest.TestCase):
    def test_surface_keeps_noindex_and_user_decision_boundary(self) -> None:
        self.assertIn('<meta name="robots" content="noindex,nofollow">', HTML)
        self.assertIn("最後決定由你確認", HTML)
        self.assertIn("建立並分析計畫", HTML)
        self.assertIn('min="2000-01-01" max="2100-12-31"', HTML)
        for name in (
            "store_type",
            "location_city",
            "location_area",
            "budget_range",
            "opening_date",
        ):
            self.assertIn(f'name="{name}"', HTML)
        for name in (
            "location",
            "budget",
            "acquired_documents",
            "missing_documents",
            "completed_items",
            "pending_items",
        ):
            self.assertIn(f"{name}:", JAVASCRIPT)

    def test_dynamic_rendering_does_not_use_inner_html(self) -> None:
        self.assertNotIn("innerHTML", HTML + JAVASCRIPT)
        self.assertIn("textContent", JAVASCRIPT)
        self.assertIn("開店規劃代理已完成分析", JAVASCRIPT)
        self.assertNotIn("manager_explanation", JAVASCRIPT)
        self.assertIn("只依原始資料獨立重算", JAVASCRIPT)
        self.assertIn('$("retry").hidden = false', JAVASCRIPT)
        self.assertNotIn("<script>", HTML)
        self.assertNotIn("<style>", HTML)
        self.assertIn("min-height: 44px", STYLESHEET)

    def test_live_endpoint_is_disabled_by_default(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(live_endpoint_enabled())
        with patch.dict("os.environ", {"STORE_READY_ENABLE_LIVE": "1"}, clear=True):
            self.assertTrue(live_endpoint_enabled())

    def test_disabled_live_endpoint_never_calls_bedrock_boundary(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/live-analyze",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with (
                patch.dict("os.environ", {}, clear=True),
                patch("store_ready.web_app.run_live_analysis") as live_boundary,
                self.assertRaises(HTTPError) as error,
            ):
                urlopen(request)
            self.assertEqual(error.exception.code, 503)
            live_boundary.assert_not_called()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_extreme_opening_date_returns_controlled_http_400(self) -> None:
        previous_cwd = os.getcwd()
        with TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            opener = build_opener(HTTPCookieProcessor(CookieJar()))
            try:
                with opener.open(base_url + "/api/session") as response:
                    csrf_token = json.loads(response.read())["csrf_token"]
                payload = {
                    "store_type": "虛構測試店",
                    "location": "虛構地點",
                    "budget": 800000,
                    "opening_date": "0001-01-01",
                    "acquired_documents": [],
                    "missing_documents": [],
                    "completed_items": [],
                    "pending_items": [],
                }
                with self.assertRaises(HTTPError) as invalid_date:
                    opener.open(
                        Request(
                            base_url + "/api/analyze",
                            data=json.dumps(payload).encode(),
                            headers={
                                "Content-Type": "application/json",
                                "X-CSRF-Token": csrf_token,
                            },
                            method="POST",
                        )
                    )
                self.assertEqual(invalid_date.exception.code, 400)
                self.assertEqual(
                    json.loads(invalid_date.exception.read())["error"], "INVALID_OPENING_DATE"
                )
                with opener.open(base_url + "/health") as response:
                    self.assertEqual(response.status, 200)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
                os.chdir(previous_cwd)

    def test_approval_is_bound_to_one_demo_browser_session(self) -> None:
        first_session, first_csrf = _new_demo_session()
        second_session, _ = _new_demo_session()
        _bind_approval(991_001, first_session)
        self.assertEqual(_session_csrf(first_session), first_csrf)
        self.assertTrue(_approval_belongs_to_session(991_001, first_session))
        self.assertFalse(_approval_belongs_to_session(991_001, second_session))

    def test_session_limit_evicts_only_oldest_session_and_its_approvals(self) -> None:
        with _session_lock:
            saved_sessions = _demo_sessions.copy()
            saved_owners = _approval_owners.copy()
            saved_project_owners = _project_owners.copy()
            _demo_sessions.clear()
            _approval_owners.clear()
            _project_owners.clear()
        try:
            oldest, _ = _new_demo_session()
            _bind_approval(991_002, oldest)
            _bind_project("oldest-project", oldest)
            for _ in range(999):
                _new_demo_session()
            newest, _ = _new_demo_session()
            self.assertIsNone(_session_csrf(oldest))
            self.assertIsNotNone(_session_csrf(newest))
            self.assertEqual(len(_demo_sessions), 1_000)
            self.assertFalse(_approval_belongs_to_session(991_002, oldest))
            self.assertFalse(_project_belongs_to_session("oldest-project", oldest))
        finally:
            with _session_lock:
                _demo_sessions.clear()
                _demo_sessions.update(saved_sessions)
                _approval_owners.clear()
                _approval_owners.update(saved_owners)
                _project_owners.clear()
                _project_owners.update(saved_project_owners)

    def test_session_expiry_removes_csrf_and_owned_resources(self) -> None:
        session_id, _ = _new_demo_session(now=100)
        _bind_approval(991_003, session_id)
        _bind_project("expiring-project", session_id)
        self.assertIsNone(_session_csrf(session_id, now=100 + SESSION_TTL_SECONDS + 1))
        with _session_lock:
            self.assertNotIn(991_003, _approval_owners)
            self.assertNotIn("expiring-project", _project_owners)

    def test_session_analysis_rate_limit_is_fail_closed(self) -> None:
        session_id, _ = _new_demo_session(now=200)
        for _ in range(MAX_ANALYSES_PER_MINUTE):
            _reserve_analysis(session_id, now=200)
        with self.assertRaisesRegex(DemoLimitExceeded, "DEMO_ANALYSIS_LIMIT_REACHED"):
            _reserve_analysis(session_id, now=200)

    def test_session_total_analysis_limit_is_fail_closed(self) -> None:
        session_id, _ = _new_demo_session(now=300)
        for index in range(MAX_ANALYSES_PER_SESSION):
            _reserve_analysis(session_id, now=300 + index * 61)
        with self.assertRaisesRegex(DemoLimitExceeded, "DEMO_ANALYSIS_LIMIT_REACHED"):
            _reserve_analysis(session_id, now=300 + MAX_ANALYSES_PER_SESSION * 61)

    def test_http_csrf_session_one_shot_and_secure_cookie_boundaries(self) -> None:
        previous_cwd = os.getcwd()
        with TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            first = build_opener(HTTPCookieProcessor(CookieJar()))
            second = build_opener(HTTPCookieProcessor(CookieJar()))

            def request_json(opener: object, request: Request) -> dict[str, object]:
                with opener.open(request) as response:  # type: ignore[attr-defined]
                    return cast(dict[str, object], json.loads(response.read()))

            try:
                first_session = request_json(first, Request(base_url + "/api/session"))
                first_csrf = str(first_session["csrf_token"])
                analysis_body = json.dumps(
                    {
                        "store_type": "虛構測試店",
                        "location": "虛構地點",
                        "budget": 800000,
                        "opening_date": "2026-10-30",
                        "acquired_documents": ["租約"],
                        "missing_documents": ["消防資料"],
                        "completed_items": ["確認租約與店址"],
                        "pending_items": [],
                    }
                ).encode()
                analyze = Request(
                    base_url + "/api/analyze",
                    data=analysis_body,
                    headers={
                        "Content-Type": "application/json",
                        "X-CSRF-Token": first_csrf,
                    },
                    method="POST",
                )
                analyzed = request_json(first, analyze)
                project_id = str(analyzed["project_id"])
                approval_id = int(analyzed["approval_request"]["id"])  # type: ignore[index]
                approval_url = base_url + f"/api/approval/{approval_id}"
                decision_body = json.dumps({"decision": "deferred"}).encode()

                audit_url = base_url + f"/api/project/{project_id}/audit"
                audit = request_json(first, Request(audit_url))
                self.assertEqual(len(cast(list[object], audit["events"])), 1)
                with first.open(Request(base_url + f"/api/report/{project_id}")) as report:
                    self.assertIn("attachment", report.headers["Content-Disposition"])

                with self.assertRaises(HTTPError) as missing_csrf:
                    first.open(
                        Request(
                            approval_url,
                            data=decision_body,
                            headers={"Content-Type": "application/json"},
                            method="POST",
                        )
                    )
                self.assertEqual(missing_csrf.exception.code, 403)

                second_session = request_json(second, Request(base_url + "/api/session"))
                for protected_url in (audit_url, base_url + f"/api/report/{project_id}"):
                    with self.subTest(protected_url=protected_url):
                        with self.assertRaises(HTTPError) as cross_project:
                            second.open(Request(protected_url))
                        self.assertEqual(cross_project.exception.code, 403)
                with self.assertRaises(HTTPError) as cross_session:
                    second.open(
                        Request(
                            approval_url,
                            data=decision_body,
                            headers={
                                "Content-Type": "application/json",
                                "X-CSRF-Token": str(second_session["csrf_token"]),
                            },
                            method="POST",
                        )
                    )
                self.assertEqual(cross_session.exception.code, 403)

                accepted = request_json(
                    first,
                    Request(
                        approval_url,
                        data=decision_body,
                        headers={
                            "Content-Type": "application/json",
                            "X-CSRF-Token": first_csrf,
                        },
                        method="POST",
                    ),
                )
                self.assertEqual(accepted["decision"], "deferred")
                with first.open(Request(base_url + f"/api/report/{project_id}")) as report:
                    updated_report = json.loads(report.read())
                self.assertEqual(updated_report["approval_request"]["status"], "deferred")
                self.assertEqual(updated_report["human_decision"]["decision"], "deferred")
                audit = request_json(first, Request(audit_url))
                self.assertEqual(len(cast(list[object], audit["events"])), 2)
                with self.assertRaises(HTTPError) as repeated:
                    first.open(
                        Request(
                            approval_url,
                            data=decision_body,
                            headers={
                                "Content-Type": "application/json",
                                "X-CSRF-Token": first_csrf,
                            },
                            method="POST",
                        )
                    )
                self.assertEqual(repeated.exception.code, 400)

                with urlopen(
                    Request(
                        base_url + "/api/session",
                        headers={"X-Forwarded-Proto": "https"},
                    )
                ) as response:
                    self.assertIn("; Secure", response.headers["Set-Cookie"])

                for asset, content_type in (
                    ("/assets/app.css", "text/css"),
                    ("/assets/app.js", "text/javascript"),
                ):
                    with urlopen(base_url + asset) as response:
                        self.assertTrue(response.headers["Content-Type"].startswith(content_type))
                        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
                        self.assertIn(
                            "default-src 'self'",
                            response.headers["Content-Security-Policy"],
                        )

                for _ in range(MAX_ANALYSES_PER_MINUTE - 1):
                    request_json(
                        first,
                        Request(
                            base_url + "/api/analyze",
                            data=analysis_body,
                            headers={
                                "Content-Type": "application/json",
                                "X-CSRF-Token": first_csrf,
                            },
                            method="POST",
                        ),
                    )
                with self.assertRaises(HTTPError) as rate_limited:
                    first.open(
                        Request(
                            base_url + "/api/analyze",
                            data=analysis_body,
                            headers={
                                "Content-Type": "application/json",
                                "X-CSRF-Token": first_csrf,
                            },
                            method="POST",
                        )
                    )
                self.assertEqual(rate_limited.exception.code, 429)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
