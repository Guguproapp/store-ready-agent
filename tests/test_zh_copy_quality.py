import unittest

from store_ready.web_app import HTML, JAVASCRIPT, STYLESHEET


class ChineseCopyQualityTests(unittest.TestCase):
    def test_product_copy_uses_plain_language(self) -> None:
        combined = HTML + JAVASCRIPT
        for unclear in (
            "決定性工具",
            "固定規則工具",
            "不可變基線",
            "不處理衝擊",
            "受波及工作",
            "追回／殘餘",
            "確認採用所選策略",
            "下載資料檔",
            "不保存秘密",
            "開幕保命線",
        ):
            self.assertNotIn(unclear, combined)
        for plain in (
            "系統計算",
            "原計畫（不會更改）",
            "不處理延誤",
            "受影響工作",
            "追回天數／剩餘延誤",
            "確認記錄此選擇",
            "下載報告資料檔",
            "不保存密碼或金鑰",
            "開幕延誤模擬",
        ):
            self.assertIn(plain, combined)

    def test_schedule_and_budget_terms_are_clear(self) -> None:
        self.assertNotIn(">浮時<", HTML)
        self.assertIn("可延後天數", HTML)
        self.assertIn("目前落後", HTML)
        self.assertIn("尚未提供預算明細", JAVASCRIPT)
        self.assertIn("有金額資料時再填預算明細", HTML)

    def test_internal_codes_have_safe_fallback_copy(self) -> None:
        self.assertIn('general: "其他風險"', JAVASCRIPT)
        self.assertIn('|| "其他風險"', JAVASCRIPT)
        self.assertNotIn("|| risk.kind", JAVASCRIPT)
        self.assertIn("目前無法完成這項操作，請稍後重試", JAVASCRIPT)
        self.assertNotIn("rescueBlockerLabels[item] || item", JAVASCRIPT)
        self.assertNotIn("taskNames.get(taskId) || taskId", JAVASCRIPT)

    def test_browser_network_errors_are_localized(self) -> None:
        self.assertIn("friendlyErrorMessage", JAVASCRIPT)
        self.assertIn("目前無法連線到服務，請稍後再試", JAVASCRIPT)
        self.assertNotIn("`執行失敗：${error.message}`", JAVASCRIPT)
        self.assertNotIn("`救援模擬失敗：${error.message}`", JAVASCRIPT)
        self.assertNotIn("`決定失敗：${error.message}`", JAVASCRIPT)
        self.assertNotIn("`方案記錄失敗：${error.message}`", JAVASCRIPT)

    def test_offline_and_live_descriptions_are_not_confused(self) -> None:
        self.assertIn("系統計算與複核", JAVASCRIPT)
        self.assertIn("雙代理複核", JAVASCRIPT)
        self.assertIn("只依原始資料獨立重算", JAVASCRIPT)
        self.assertNotIn(": data.reviewer_report.review_mode", JAVASCRIPT)

    def test_mobile_progress_copy_can_wrap(self) -> None:
        self.assertIn("white-space: normal", STYLESHEET)


if __name__ == "__main__":
    unittest.main()
