import re
import unittest
from http.cookiejar import CookieJar
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import HTTPCookieProcessor, build_opener, urlopen

from store_ready.web_app import ENGLISH_HTML, ENGLISH_JAVASCRIPT, HTML, JAVASCRIPT, Handler


class BilingualEntryTests(unittest.TestCase):
    def test_english_sources_are_complete_and_language_pure(self) -> None:
        self.assertIn('<html lang="en">', ENGLISH_HTML)
        self.assertIn('<meta name="robots" content="noindex,nofollow">', ENGLISH_HTML)
        self.assertIn('src="/assets/app-en.js?v=15"', ENGLISH_HTML)
        self.assertIn('href="/"', ENGLISH_HTML)
        self.assertIn("Human approval", ENGLISH_HTML)
        self.assertIn("Launch rescue", ENGLISH_HTML)
        self.assertNotRegex(ENGLISH_HTML, r"[\u3400-\u9fff]")
        self.assertNotIn("innerHTML", ENGLISH_HTML + ENGLISH_JAVASCRIPT)
        self.assertIn("textContent", ENGLISH_JAVASCRIPT)

    def test_english_runtime_preserves_canonical_store_values(self) -> None:
        for canonical in (
            "街邊咖啡店",
            "美容／美髮／美甲工作室",
            "健身／運動工作室",
            "一般零售門市",
        ):
            self.assertIn(canonical, ENGLISH_JAVASCRIPT)
        self.assertIn("canonicalStoreTypes", ENGLISH_JAVASCRIPT)
        self.assertIn("translatePayload", ENGLISH_JAVASCRIPT)

    def test_server_exposes_both_language_entries(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        try:
            with opener.open(f"http://127.0.0.1:{server.server_port}/") as response:
                chinese = response.read().decode()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["Content-Language"], "zh-Hant")
                self.assertIn('href="/en"', chinese)
            with opener.open(f"http://127.0.0.1:{server.server_port}/en") as response:
                english = response.read().decode()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["Content-Language"], "en")
                self.assertIn('<html lang="en">', english)
            with urlopen(f"http://127.0.0.1:{server.server_port}/assets/app-en.js") as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read().decode(), ENGLISH_JAVASCRIPT)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_english_copy_has_no_untranslated_user_facing_tokens(self) -> None:
        visible_source = re.sub(r"[\s\n]+", " ", ENGLISH_HTML)
        for token in ("新臺幣", "尚未", "開幕", "準備度", "核准", "稽核"):
            self.assertNotIn(token, visible_source)

    def test_english_copy_avoids_internal_or_vague_jargon(self) -> None:
        for token in (
            "Immutable baseline",
            "Opening-day lifeline",
            "Fixed rules",
            ">Float<",
            ">Download data<",
        ):
            self.assertNotIn(token, ENGLISH_HTML + ENGLISH_JAVASCRIPT)

    def test_english_runtime_only_references_existing_controls(self) -> None:
        html_ids = set(re.findall(r'id="([^"]+)"', ENGLISH_HTML))
        runtime_ids = set(re.findall(r'\$\("([^"]+)"\)', ENGLISH_JAVASCRIPT))
        self.assertEqual(runtime_ids - html_ids, set())

    def test_both_runtimes_retry_session_and_fail_closed_during_rescue(self) -> None:
        for source in (JAVASCRIPT, ENGLISH_JAVASCRIPT):
            self.assertIn("const ensureSession", source)
            self.assertIn("sessionRequest = null", source)
            self.assertNotIn("const sessionReady", source)
            self.assertIn("rescueSimulationId = null", source)
            self.assertIn('$("rescue-result").hidden = true', source)
            self.assertIn('if (busy) $("adopt-rescue").disabled = true', source)

        self.assertIn('aria-label="Readiness score"', ENGLISH_HTML)
        self.assertIn('src="/assets/app.js?v=14"', HTML)


if __name__ == "__main__":
    unittest.main()
