import os
import unittest
from pathlib import Path
from unittest import mock

from cockpit_mcp.service import CockpitService, CockpitStore


ROOT = Path(__file__).resolve().parents[2]


class CockpitMCPServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = CockpitService(ROOT)

    def test_status_reads_all_contracts(self):
        result = self.service.status()
        self.assertGreater(result["asset_count"], 1000)
        self.assertGreater(result["news_count"], 0)
        self.assertGreater(result["video_count"], 0)
        self.assertEqual(result["mode"], "read_only")
        self.assertEqual(result["contract_health"]["source_mode"], "local_files")

    def test_remote_contract_mode_uses_published_json(self):
        raw = (ROOT / "data.json").read_bytes()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, _):
                return raw

        with mock.patch.dict(os.environ, {
            "COCKPIT_DATA_BASE_URL": "https://example.test/cockpit",
            "COCKPIT_REMOTE_CACHE_SECONDS": "30",
        }), mock.patch("cockpit_mcp.service.urllib.request.urlopen", return_value=Response()) as opener:
            store = CockpitStore(ROOT)
            payload = store.load("data.json")
            self.assertEqual(payload.get("timestamp"), self.service.status().get("payload_timestamp"))
            self.assertEqual(store.health()["source_mode"], "remote_live")
            self.assertEqual(store.health()["last_fetch_errors"], {})
            self.assertEqual(opener.call_count, 1)
            store.load("data.json")
            self.assertEqual(opener.call_count, 1)

    def test_telemetry_heatmap_and_trending_are_explicit(self):
        telemetry = self.service.market_telemetry("^JKSE")
        self.assertEqual(len(telemetry["results"]), 1)
        self.assertTrue(telemetry["results"][0]["source_url"])

        heatmap = self.service.heatmap("ID", limit=25)
        self.assertGreater(heatmap["total_matches"], 100)
        self.assertLessEqual(len(heatmap["results"]), 25)
        self.assertTrue(heatmap["by_sector"])

        trending = self.service.trending("id", "gainers")
        self.assertIsInstance(trending["results"], list)

    def test_macro_indicators_preserve_release_periods_and_sources(self):
        core = self.service.macro_indicators("core")
        self.assertEqual(core["status"], "ok")
        self.assertGreaterEqual(len(core["results"]), 12)
        self.assertTrue(all(item["reference_period"] for item in core["results"]))
        self.assertTrue(all(item["source_url"].startswith("http") for item in core["results"]))
        prices = self.service.macro_indicators("core", "Prices")
        self.assertGreaterEqual(len(prices["results"]), 3)
        self.assertTrue(all(item["pillar"] == "Prices" for item in prices["results"]))
        ratings = self.service.macro_indicators("ratings")
        self.assertEqual(ratings["status"], "ok")
        self.assertEqual(len(ratings["results"]), 5)

    def test_exact_idx_asset_includes_provenance_and_score(self):
        result = self.service.get_asset("BBCA", "ID")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["country"], "ID")
        self.assertTrue(result["source"]["url"])
        self.assertIsNotNone(result["score"])

    def test_asset_search_supports_industry(self):
        result = self.service.search_assets("bank", "ID", limit=8)
        self.assertGreater(result["total_matches"], 0)
        self.assertLessEqual(len(result["results"]), 8)

    def test_chart_returns_quality_and_bounded_points(self):
        result = self.service.get_chart("BBCA", "1M", "ID")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["chart_quality"])
        self.assertGreater(result["point_count"], 1)
        self.assertLessEqual(result["point_count"], 40)

    def test_score_detail_exposes_real_metrics_and_warnings(self):
        result = self.service.get_score("BBCA", "ID")
        self.assertEqual(result["status"], "ok")
        self.assertIn("metrics", result)
        self.assertIn("data_warnings", result)

    def test_news_is_source_linked_and_summary_basis_is_explicit(self):
        result = self.service.search_news(market="ID", window_days=7, limit=10)
        self.assertGreater(len(result["results"]), 0)
        for item in result["results"]:
            self.assertTrue(item["url"])
            self.assertIn(item["summary_basis"], ("publisher excerpt", "headline and metadata only"))

        detail = self.service.get_news(result["results"][0]["url"])
        self.assertEqual(detail["status"], "ok")
        self.assertEqual(detail["news"]["url"], result["results"][0]["url"])

    def test_video_and_knowledge_search_exposes_summary_basis(self):
        result = self.service.search_videos(include_knowledge=True, limit=10)
        self.assertGreater(len(result["results"]), 0)
        for item in result["results"]:
            self.assertTrue(item["video_id"])
            self.assertTrue(item["url"])
            self.assertTrue(item["summary_basis"])

    def test_research_search_and_detail_preserve_publisher_provenance(self):
        report = {
            "id": "live-bbca", "title": "BBCA Company Update", "publisher": "Test Broker",
            "published": "2026-07-20", "published_ts": 1784505600, "priority": "Live",
            "category": "Equity Research", "report_type": "Equity Research",
            "category_detail": "Public Markets", "subcategory": "Company / Equity",
            "geography": "Indonesia", "geography_detail": "Indonesia / ASEAN",
            "ticker_tags": ["BBCA"], "access": "Open",
            "source_url": "https://example.com/bbca", "landing_url": "https://example.com/bbca",
            "source_type": "official_discovery", "summary_basis": "publisher excerpt",
        }
        payload = {"timestamp": "2026-07-20T00:00:00Z", "research": {
            "reports": [report], "health": {"status": "ready"},
            "provenance_note": "Source-linked metadata.",
        }}
        with mock.patch.object(self.service, "_snapshot", return_value=(payload, {}, {})):
            result = self.service.search_research(ticker="BBCA")
            self.assertEqual(result["total_matches"], 1)
            self.assertEqual(result["results"][0]["publisher"], "Test Broker")
            self.assertEqual(result["results"][0]["report_type"], "Equity Research")
            self.assertEqual(result["results"][0]["geography_detail"], "Indonesia / ASEAN")
            detail = self.service.get_research("live-bbca")
            self.assertEqual(detail["status"], "ok")
            self.assertEqual(detail["research"]["source_url"], "https://example.com/bbca")

    def test_company_evidence_keeps_evidence_layers_separate(self):
        with mock.patch.object(self.service, "get_asset", return_value={"status": "ok", "sector": "financials"}), \
                mock.patch.object(self.service, "get_score", return_value={"status": "ok", "score": 80}), \
                mock.patch.object(self.service, "get_chart", return_value={"status": "ok", "points": []}), \
                mock.patch.object(self.service, "search_news", return_value={"results": [{"title": "News"}]}), \
                mock.patch.object(self.service, "search_videos", return_value={"results": [{"title": "Video"}]}), \
                mock.patch.object(self.service, "search_research", side_effect=[
                    {"results": [{"title": "Broker report"}]},
                ]):
            result = self.service.company_evidence("BBCA", "ID")
        self.assertEqual(result["research"][0]["title"], "Broker report")
        self.assertIn("provider facts", result["provenance_rules"][0].lower())

    def test_daily_brief_contains_news_and_video_synthesis(self):
        result = self.service.market_sentiment()
        self.assertIn("sentiment", result)
        self.assertIn("news_digest", result)
        self.assertIn("video_digest", result)

    def test_intelligence_brief_combines_cross_media_evidence(self):
        result = self.service.intelligence_brief(ticker="BBCA", market="ID", window_days=7)
        self.assertEqual(result["asset"]["status"], "ok")
        self.assertIn("news", result)
        self.assertIn("videos", result)
        self.assertIn("research", result)
        self.assertIn("macro_indicators", result)
        self.assertIn("grounding_rules", result)

    def test_ipo_radar_preserves_health_and_synthesis(self):
        result = self.service.ipo_radar("recent", "ID", 20)
        self.assertEqual(result["status"], "ok")
        self.assertIn("health", result)
        self.assertIn("synthesis", result)


if __name__ == "__main__":
    unittest.main()
