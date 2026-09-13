"""Dependency-free StoreReady web application and secured DEMO API."""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from collections import OrderedDict
from dataclasses import dataclass, field
from hmac import compare_digest
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Any

from .agents import (
    LivePreflightFailed,
    evidence_document,
    run_live_analysis,
    run_live_rescue_review,
)
from .domain import default_tasks
from .preflight import CredentialsRequired, load_preflight_config
from .service import (
    _budget_items,
    analyze_payload,
    apply_human_decision,
    create_rescue_simulation,
    demo_payload,
    parse_project_payload,
    record_rescue_agent_review,
    record_rescue_strategy,
)
from .storage import connect

MAX_REQUEST_BYTES = 64 * 1024
SESSION_TTL_SECONDS = 7_200
MAX_DEMO_SESSIONS = 1_000
MAX_ANALYSES_PER_MINUTE = 5
MAX_ANALYSES_PER_SESSION = 20
ANALYSIS_WINDOW_SECONDS = 60
PACKAGE_ROOT = Path(__file__).resolve().parent
HTML = (PACKAGE_ROOT / "templates" / "index.html").read_text()
ENGLISH_HTML = (PACKAGE_ROOT / "templates" / "index_en.html").read_text()
STYLESHEET = (PACKAGE_ROOT / "static" / "app.css").read_text()
JAVASCRIPT = (PACKAGE_ROOT / "static" / "app.js").read_text()
ENGLISH_JAVASCRIPT = (PACKAGE_ROOT / "static" / "app-en.js").read_text()
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
    "form-action 'self'"
)

_session_lock = Lock()


@dataclass
class DemoSession:
    csrf_token: str
    expires_at: float
    analysis_count: int = 0
    recent_analyses: list[float] = field(default_factory=list)


class DemoLimitExceeded(RuntimeError):
    """Raised when a public DEMO session exceeds its bounded usage."""


_demo_sessions: OrderedDict[str, DemoSession] = OrderedDict()
_approval_owners: dict[int, str] = {}
_project_owners: dict[str, str] = {}


def live_endpoint_enabled() -> bool:
    """Paid Live Agent calls are opt-in and disabled in public DEMO deployments."""

    return os.getenv("STORE_READY_ENABLE_LIVE") == "1"


def _cookie_session(cookie_header: str | None) -> str | None:
    cookie = SimpleCookie()
    cookie.load(cookie_header or "")
    value = cookie.get("store_ready_session")
    return value.value if value is not None else None


def _remove_session_locked(session_id: str) -> None:
    _demo_sessions.pop(session_id, None)
    expired_approvals = [
        approval_id for approval_id, owner in _approval_owners.items() if owner == session_id
    ]
    expired_projects = [
        project_id for project_id, owner in _project_owners.items() if owner == session_id
    ]
    for approval_id in expired_approvals:
        _approval_owners.pop(approval_id, None)
    for project_id in expired_projects:
        _project_owners.pop(project_id, None)


def _purge_expired_sessions_locked(now: float) -> None:
    expired = [
        session_id for session_id, session in _demo_sessions.items() if session.expires_at <= now
    ]
    for session_id in expired:
        _remove_session_locked(session_id)


def _new_demo_session(now: float | None = None) -> tuple[str, str]:
    current = monotonic() if now is None else now
    with _session_lock:
        _purge_expired_sessions_locked(current)
        while len(_demo_sessions) >= MAX_DEMO_SESSIONS:
            oldest_session = next(iter(_demo_sessions))
            _remove_session_locked(oldest_session)
        session_id = secrets.token_urlsafe(24)
        csrf_token = secrets.token_urlsafe(32)
        _demo_sessions[session_id] = DemoSession(
            csrf_token=csrf_token,
            expires_at=current + SESSION_TTL_SECONDS,
        )
    return session_id, csrf_token


def _session_csrf(session_id: str | None, now: float | None = None) -> str | None:
    if session_id is None:
        return None
    current = monotonic() if now is None else now
    with _session_lock:
        _purge_expired_sessions_locked(current)
        session = _demo_sessions.get(session_id)
        return session.csrf_token if session is not None else None


def _reserve_analysis(session_id: str, now: float | None = None) -> None:
    current = monotonic() if now is None else now
    with _session_lock:
        _purge_expired_sessions_locked(current)
        session = _demo_sessions.get(session_id)
        if session is None:
            raise PermissionError("DEMO_SESSION_REQUIRED")
        session.recent_analyses = [
            item for item in session.recent_analyses if current - item < ANALYSIS_WINDOW_SECONDS
        ]
        if (
            len(session.recent_analyses) >= MAX_ANALYSES_PER_MINUTE
            or session.analysis_count >= MAX_ANALYSES_PER_SESSION
        ):
            raise DemoLimitExceeded("DEMO_ANALYSIS_LIMIT_REACHED")
        session.recent_analyses.append(current)
        session.analysis_count += 1


def _bind_approval(approval_id: int, session_id: str) -> None:
    with _session_lock:
        _approval_owners[approval_id] = session_id


def _approval_belongs_to_session(approval_id: int, session_id: str) -> bool:
    with _session_lock:
        _purge_expired_sessions_locked(monotonic())
        return _approval_owners.get(approval_id) == session_id


def _bind_project(project_id: str, session_id: str) -> None:
    with _session_lock:
        _project_owners[project_id] = session_id


def _project_belongs_to_session(project_id: str, session_id: str) -> bool:
    with _session_lock:
        _purge_expired_sessions_locked(monotonic())
        return _project_owners.get(project_id) == session_id


class Handler(BaseHTTPRequestHandler):
    """Serve the product surface without exposing Agent or decision privileges."""

    def _ensure_demo_session(self) -> tuple[str, str, str | None]:
        session_id = _cookie_session(self.headers.get("Cookie"))
        csrf_token = _session_csrf(session_id)
        if session_id is not None and csrf_token is not None:
            return session_id, csrf_token, None
        session_id, csrf_token = _new_demo_session()
        secure = "; Secure" if self.headers.get("X-Forwarded-Proto", "").lower() == "https" else ""
        cookie = (
            f"store_ready_session={session_id}; Path=/; HttpOnly; "
            f"SameSite=Strict; Max-Age={SESSION_TTL_SECONDS}{secure}"
        )
        return session_id, csrf_token, cookie

    def _require_demo_session(self) -> tuple[str, str]:
        session_id = _cookie_session(self.headers.get("Cookie"))
        csrf_token = _session_csrf(session_id)
        if session_id is None or csrf_token is None:
            raise PermissionError("DEMO_SESSION_REQUIRED")
        return session_id, csrf_token

    def _send(
        self,
        status: HTTPStatus,
        body: bytes,
        content_type: str,
        *,
        set_cookie: str | None = None,
        download: bool = False,
        cache_control: str = "no-store",
        content_language: str | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        if content_language is not None:
            self.send_header("Content-Language", content_language)
        if set_cookie is not None:
            self.send_header("Set-Cookie", set_cookie)
        if download:
            self.send_header("Content-Disposition", "attachment; filename=readiness-report.json")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        self._send(
            status,
            json.dumps(payload, ensure_ascii=False).encode(),
            "application/json; charset=utf-8",
        )

    def _database(self) -> Path:
        return Path("data") / "store_ready.sqlite3"

    def _project_id_from(self, prefix: str, suffix: str = "") -> str | None:
        path = self.path.split("?", 1)[0]
        if not path.startswith(prefix):
            return None
        value = path[len(prefix) :]
        if suffix:
            if not value.endswith(suffix):
                return None
            value = value[: -len(suffix)]
        return value if value and "/" not in value and len(value) <= 64 else None

    def _owned_project(self, project_id: str) -> str:
        session_id, _ = self._require_demo_session()
        if not _project_belongs_to_session(project_id, session_id):
            raise PermissionError("PROJECT_SESSION_MISMATCH")
        return session_id

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            if path == "/":
                _, _, set_cookie = self._ensure_demo_session()
                self._send(
                    HTTPStatus.OK,
                    HTML.encode(),
                    "text/html; charset=utf-8",
                    set_cookie=set_cookie,
                    content_language="zh-Hant",
                )
                return
            if path == "/en":
                _, _, set_cookie = self._ensure_demo_session()
                self._send(
                    HTTPStatus.OK,
                    ENGLISH_HTML.encode(),
                    "text/html; charset=utf-8",
                    set_cookie=set_cookie,
                    content_language="en",
                )
                return
            if path == "/assets/app.css":
                self._send(
                    HTTPStatus.OK,
                    STYLESHEET.encode(),
                    "text/css; charset=utf-8",
                    cache_control="public, max-age=3600",
                )
                return
            if path == "/assets/app.js":
                self._send(
                    HTTPStatus.OK,
                    JAVASCRIPT.encode(),
                    "text/javascript; charset=utf-8",
                    cache_control="public, max-age=3600",
                )
                return
            if path == "/assets/app-en.js":
                self._send(
                    HTTPStatus.OK,
                    ENGLISH_JAVASCRIPT.encode(),
                    "text/javascript; charset=utf-8",
                    cache_control="public, max-age=3600",
                )
                return
            if path == "/health":
                self._send_json(
                    HTTPStatus.OK,
                    {"status": "ok", "check": "liveness", "model_called": False},
                )
                return
            if path == "/ready":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "status": "ready",
                        "check": "readiness",
                        "mode": "demo",
                        "live_enabled": live_endpoint_enabled(),
                        "model_called": False,
                    },
                )
                return
            if path == "/api/session":
                _, csrf_token, set_cookie = self._ensure_demo_session()
                body = json.dumps({"csrf_token": csrf_token}).encode()
                self._send(
                    HTTPStatus.OK,
                    body,
                    "application/json; charset=utf-8",
                    set_cookie=set_cookie,
                )
                return
            if path == "/api/demo":
                self._send_json(HTTPStatus.OK, analyze_payload(demo_payload()))
                return

            report_project_id = self._project_id_from("/api/report/")
            if report_project_id is not None:
                self._owned_project(report_project_id)
                database = self._database()
                if not database.exists():
                    raise LookupError("REPORT_NOT_FOUND")
                with connect(str(database)) as connection:
                    row = connection.execute(
                        "SELECT content_json FROM readiness_report WHERE project_id = ? "
                        "ORDER BY id DESC LIMIT 1",
                        (report_project_id,),
                    ).fetchone()
                if row is None:
                    raise LookupError("REPORT_NOT_FOUND")
                self._send(
                    HTTPStatus.OK,
                    str(row[0]).encode(),
                    "application/json; charset=utf-8",
                    download=True,
                )
                return

            audit_project_id = self._project_id_from("/api/project/", "/audit")
            if audit_project_id is not None:
                self._owned_project(audit_project_id)
                database = self._database()
                if not database.exists():
                    raise LookupError("PROJECT_NOT_FOUND")
                with connect(str(database)) as connection:
                    rows = connection.execute(
                        "SELECT event_type, detail, created_at FROM audit_event "
                        "WHERE project_id = ? ORDER BY id DESC LIMIT 50",
                        (audit_project_id,),
                    ).fetchall()
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "events": [
                            {
                                "event_type": str(row[0]),
                                "detail": str(row[1]),
                                "created_at": str(row[2]),
                            }
                            for row in rows
                        ]
                    },
                )
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "NOT_FOUND"})
        except PermissionError as exc:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
        except (LookupError, sqlite3.Error) as exc:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        rescue_project_id = self._project_id_from("/api/rescue/")
        live_rescue_project_id = self._project_id_from("/api/live-rescue/")
        rescue_simulation_id = self._project_id_from("/api/rescue-decision/")
        if not (
            path in {"/api/analyze", "/api/live-analyze"}
            or path.startswith("/api/approval/")
            or rescue_project_id is not None
            or live_rescue_project_id is not None
            or rescue_simulation_id is not None
        ):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "NOT_FOUND"})
            return
        if (
            path == "/api/live-analyze" or live_rescue_project_id is not None
        ) and not live_endpoint_enabled():
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": "LIVE_AGENT_DISABLED_FOR_PUBLIC_DEMO"},
            )
            return
        try:
            session_id, csrf_token = self._require_demo_session()
            provided_csrf = self.headers.get("X-CSRF-Token", "")
            if not provided_csrf or not compare_digest(provided_csrf, csrf_token):
                raise PermissionError("CSRF_REQUIRED")
            if not self.headers.get("Content-Type", "").lower().startswith("application/json"):
                raise ValueError("JSON_CONTENT_TYPE_REQUIRED")
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("INVALID_REQUEST_SIZE")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("INVALID_JSON_OBJECT")
            if (
                path in {"/api/analyze", "/api/live-analyze"}
                or rescue_project_id is not None
                or live_rescue_project_id is not None
            ):
                _reserve_analysis(session_id)
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            with connect(str(self._database())) as connection:
                if path == "/api/analyze":
                    output = analyze_payload(payload, connection)
                elif path == "/api/live-analyze":
                    config = load_preflight_config()
                    project = parse_project_payload(payload)
                    tasks = default_tasks(project)
                    live = run_live_analysis(
                        config,
                        project,
                        tasks,
                        _budget_items(payload),
                    )
                    output = analyze_payload(payload, connection)
                    output.update(
                        {
                            "status": "LIVE_AGENT_COMPLETE",
                            "manager_explanation": live.manager_explanation,
                            "reviewer_report": live.reviewer_report,
                            "live_agent_ids": {
                                "manager": live.evidence.manager_agent_id,
                                "reviewer": live.evidence.reviewer_agent_id,
                            },
                        }
                    )
                    evidence_path = Path("reports/live-agent-evidence") / (
                        f"live-analysis-{output['project_id']}.json"
                    )
                    evidence_path.parent.mkdir(parents=True, exist_ok=True)
                    evidence_path.write_text(
                        json.dumps(evidence_document(live.evidence), ensure_ascii=False, indent=2)
                        + "\n"
                    )
                    connection.execute(
                        "INSERT INTO audit_event(project_id, event_type, detail) VALUES (?, ?, ?)",
                        (output["project_id"], "live_two_agent_analysis_completed", "real Bedrock"),
                    )
                    connection.execute(
                        "UPDATE readiness_report SET source = ?, content_json = ? "
                        "WHERE project_id = ? AND id = (SELECT MAX(id) FROM readiness_report "
                        "WHERE project_id = ?)",
                        (
                            "live_agents",
                            json.dumps(output, ensure_ascii=False),
                            output["project_id"],
                            output["project_id"],
                        ),
                    )
                    connection.commit()
                elif live_rescue_project_id is not None:
                    self._owned_project(live_rescue_project_id)
                    output = create_rescue_simulation(
                        connection,
                        live_rescue_project_id,
                        payload,
                    )
                    snapshots = connection.execute(
                        "SELECT source_json, scenario_json FROM rescue_simulation WHERE id = ?",
                        (output["simulation_id"],),
                    ).fetchone()
                    if snapshots is None:
                        raise ValueError("RESCUE_SIMULATION_NOT_FOUND")
                    config = load_preflight_config()
                    live = run_live_rescue_review(
                        config,
                        str(snapshots[0]),
                        str(snapshots[1]),
                        {name: str(value) for name, value in output["hashes"].items()},
                    )
                    record_rescue_agent_review(
                        connection,
                        output["simulation_id"],
                        live.reviewer_report,
                    )
                    output.update(
                        {
                            "status": "LIVE_RESCUE_COMPLETE",
                            "review_status": "INDEPENDENT_REVIEW_PASSED",
                            "manager_explanation": live.manager_explanation,
                            "reviewer_report": live.reviewer_report,
                            "live_agent_ids": {
                                "manager": live.evidence.manager_agent_id,
                                "reviewer": live.evidence.reviewer_agent_id,
                            },
                        }
                    )
                    evidence_path = Path("reports/opening-rescue/live-agent-evidence") / (
                        f"live-rescue-{output['simulation_id']}.json"
                    )
                    evidence_path.parent.mkdir(parents=True, exist_ok=True)
                    evidence_path.write_text(
                        json.dumps(
                            evidence_document(live.evidence),
                            ensure_ascii=False,
                            indent=2,
                        )
                        + "\n"
                    )
                elif rescue_project_id is not None:
                    self._owned_project(rescue_project_id)
                    output = create_rescue_simulation(connection, rescue_project_id, payload)
                elif rescue_simulation_id is not None:
                    simulation = connection.execute(
                        "SELECT project_id FROM rescue_simulation WHERE id = ?",
                        (rescue_simulation_id,),
                    ).fetchone()
                    if simulation is None:
                        raise ValueError("RESCUE_SIMULATION_NOT_FOUND")
                    self._owned_project(str(simulation[0]))
                    strategy_id = payload.get("strategy_id")
                    if not isinstance(strategy_id, str):
                        raise ValueError("INVALID_RESCUE_STRATEGY")
                    output = record_rescue_strategy(
                        connection,
                        rescue_simulation_id,
                        strategy_id,
                        actor="demo_browser_session",
                    )
                else:
                    approval_id = int(path.rsplit("/", 1)[1])
                    if not _approval_belongs_to_session(approval_id, session_id):
                        raise PermissionError("APPROVAL_SESSION_MISMATCH")
                    decision = payload.get("decision")
                    if not isinstance(decision, str):
                        raise ValueError("INVALID_HUMAN_DECISION")
                    output = {
                        "decision": apply_human_decision(
                            connection,
                            approval_id,
                            decision,
                            actor="demo_browser_session",
                        )
                    }
                if path in {"/api/analyze", "/api/live-analyze"}:
                    project_id = output.get("project_id")
                    if isinstance(project_id, str):
                        _bind_project(project_id, session_id)
                    approval_id = output.get("approval_request", {}).get("id")
                    if isinstance(approval_id, int):
                        _bind_approval(approval_id, session_id)
            self._send_json(HTTPStatus.OK, output)
        except CredentialsRequired as exc:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(exc)})
        except LivePreflightFailed as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
        except DemoLimitExceeded as exc:
            self._send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": str(exc)})
        except PermissionError as exc:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
        except (ValueError, OverflowError, json.JSONDecodeError, sqlite3.Error) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    ThreadingHTTPServer((host, port), Handler).serve_forever()
