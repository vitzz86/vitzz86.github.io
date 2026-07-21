import time
import unittest

from tools import (fundamentals, idx_membership, ipos, macro_indicators,
                   news_router, research, sectors, universe)


class FinancialGuardrailTests(unittest.TestCase):
    def test_previous_score_schema_is_invalidated(self):
        row = {"source_symbol": "TEST.JK", "ticker": "TEST"}
        previous = {"TEST.JK": {"fundamental_score": {
            "schema_version": fundamentals.SCORE_SCHEMA_VERSION - 1,
            "as_of": fundamentals._now_iso(),
            "metrics": [{"label": "P/E", "value": 10}],
        }}}
        self.assertIsNone(fundamentals._previous_metrics(previous, row, 24))

    def test_extreme_provider_ratios_are_quarantined(self):
        row = {"ticker": "TEST", "name": "Test Tbk", "sector_key": "technology"}
        metrics = fundamentals._quarantine_metric_anomalies(row, {
            "current_price": 100, "market_cap": 1_000_000,
            "pe": 1_430.0, "forward_pe": 121_621.0, "pb": 105.0,
            "ev_ebitda": 300.0, "dividend_yield_pct": 247.0,
            "fcf_yield_pct": 54.0, "free_cash_flow": 540_000,
        })
        for key in ("pe", "forward_pe", "pb", "ev_ebitda", "dividend_yield_pct", "fcf_yield_pct"):
            self.assertIsNone(metrics[key])
        self.assertIsNone(metrics.get("eps"))
        self.assertGreaterEqual(len(metrics["_data_warnings"]), 6)

    def test_extreme_but_consistent_pe_keeps_eps_and_hides_multiple(self):
        metrics = fundamentals._quarantine_metric_anomalies(
            {"ticker": "TEST", "name": "Test Tbk", "sector_key": "technology"},
            {"current_price": 1_000, "eps": 2, "pe": 500, "market_cap": 1_000_000},
        )
        self.assertEqual(metrics["eps"], 2)
        self.assertIsNone(metrics["pe"])

    def test_tradingview_overrides_idx_market_sized_fields(self):
        row = {
            "country": "ID", "exchange": "IDX", "source_provider": "tradingview",
            "value": 1_500, "market_cap_value": 25_000_000_000_000,
            "volume": 2_000_000, "avg_volume_10d": 3_000_000,
        }
        metrics = fundamentals._normalize_currencies(row, {
            "currency": "IDR", "current_price": 1_480,
            "market_cap": 30_000_000_000_000, "volume": 1_000_000,
            "average_volume_10d": 1_500_000,
        })
        self.assertEqual(metrics["current_price"], 1_500)
        self.assertEqual(metrics["market_cap"], 25_000_000_000_000)
        self.assertEqual(metrics["volume"], 2_000_000)
        self.assertEqual(metrics["average_volume_10d"], 3_000_000)
        self.assertEqual(metrics["avg_daily_value_traded"], 4_500_000_000)

    def test_score_coverage_tracks_provider_fields_not_axes(self):
        score = fundamentals._pack_score("equity", [
            {"key": "value", "label": "Value", "score": 80},
            {"key": "momentum", "label": "Momentum", "score": 60},
        ], {"current_price": 100, "market_cap": 1_000_000}, None, None, None)
        self.assertEqual(score["axis_coverage"], 1.0)
        self.assertLess(score["input_coverage"], 0.5)
        self.assertEqual(score["coverage"], score["input_coverage"])

    def test_checkpoint_history_does_not_produce_risk_ratios(self):
        row = {
            "spark": [100 + i for i in range(30)],
            "chart_quality": {"6M": "performance_checkpoint"},
        }
        self.assertEqual(fundamentals._risk_stats(row, "equity"), {})
        self.assertIsNone(fundamentals._row_volatility(row))

    def test_real_closes_can_produce_risk_ratios(self):
        row = {
            "spark": [100 + (i % 5) for i in range(30)],
            "chart_quality": {"6M": "historical_close"},
        }
        self.assertIn("sharpe", fundamentals._risk_stats(row, "equity"))

    def test_idx_history_overlay_preserves_tradingview_quote(self):
        now = int(time.time())
        prices = {"TEST.JK": {
            "value": 1234,
            "delta_pct": 2.5,
            "chart_quality": {"24h": "real_intraday", "6M": "performance_checkpoint"},
        }}
        rows = [{
            "ticker": "TEST", "source_symbol": "TEST.JK", "country": "ID",
            "source_provider": "tradingview", "market_cap_value": 1_000_000,
        }]
        previous = [{"constituents": [{
            "ticker": "TEST", "source_symbol": "TEST.JK",
            "spark": [100 + i for i in range(30)],
            "spark_ts": [now - (29 - i) * 86400 for i in range(30)],
            "history_asof": now,
            "price_history_quality": "yahoo_historical_close",
            "chart_quality": {"6M": "historical_close"},
        }]}]
        sectors._idx_daily_history_overlay(prices, rows, previous)
        self.assertEqual(prices["TEST.JK"]["value"], 1234)
        self.assertEqual(prices["TEST.JK"]["delta_pct"], 2.5)
        self.assertEqual(prices["TEST.JK"]["chart_quality"]["24h"], "real_intraday")
        self.assertEqual(prices["TEST.JK"]["chart_quality"]["6M"], "historical_close")
        self.assertEqual(len(prices["TEST.JK"]["spark"]), 30)

    def test_idx_screen_uses_valid_analyst_consensus_target(self):
        score = fundamentals._score_idx_screen({
            "ticker": "TEST", "country": "ID", "value": 1_000,
            "market_cap_value": 10_000_000_000_000, "volume": 1_000_000,
            "avg_volume_10d": 1_200_000, "relative_volume_10d": 1.1,
            "analyst_target_low": 1_100, "analyst_target_median": 1_300,
            "analyst_target_high": 1_500,
        })
        valuation = score.get("valuation") or {}
        self.assertEqual(valuation.get("valuation_model"), "tradingview_analyst_consensus")
        self.assertEqual(valuation.get("target_price"), 1_300)
        self.assertEqual(valuation.get("upside_pct"), 30.0)

    def test_peer_pe_is_not_a_primary_target_anchor(self):
        metrics = {
            "current_price": 100,
            "eps": 5,
            "_sector_peer_pe": 15,
            "_ticker": "TEST",
            "_sector_key": "technology",
            "_country": "ID",
        }
        self.assertIsNone(fundamentals._valuation(metrics))

    def test_high_observed_pe_stays_anchored_to_the_stock(self):
        metrics = {
            "current_price": 100,
            "eps": 0.55,
            "pe": 181.8,
            "forward_pe": 150,
            "pb": 2,
            "roe_pct": 15,
            "_ticker": "TEST",
            "_sector_key": "renewables",
            "_country": "ID",
        }
        valuation = fundamentals._valuation(metrics)
        self.assertIsNotNone(valuation)
        self.assertGreater(valuation["fair_value"], 30)
        self.assertEqual(valuation["valuation_confidence"], "Medium")


class MacroIndicatorContractTests(unittest.TestCase):
    def test_macro_monitor_has_at_least_twelve_official_headline_cards(self):
        payload = macro_indicators.collect([])
        self.assertGreaterEqual(len(payload["core"]), 12)
        self.assertTrue(all(row["source_url"].startswith("http") for row in payload["core"]))
        self.assertTrue(all(row["update_mode"] == "official_release" for row in payload["core"]))

    def test_bi_rate_overlay_updates_only_official_policy_card(self):
        payload = macro_indicators.collect([{
            "symbol": "BI_RATE", "value": 6.0, "url": "https://example.com/bi",
            "source_name": "Bank Indonesia", "asof": "21 Jul 2026",
        }])
        row = next(item for item in payload["core"] if item["id"] == "id_bi_rate")
        self.assertEqual(row["value_display"], "6.00%")
        self.assertEqual(row["source_name"], "Bank Indonesia")

    def test_market_drivers_are_not_duplicated_in_macro_payload(self):
        payload = macro_indicators.collect([])
        self.assertNotIn("external", payload)

    def test_ratings_separate_credit_from_market_classification(self):
        payload = macro_indicators.collect([])
        ratings = payload["ratings"]
        self.assertEqual(len(ratings), 5)
        self.assertEqual({row["pillar"] for row in ratings},
                         {"Sovereign Credit", "Market Classification"})
        self.assertTrue(all(row["source_url"].startswith("http") for row in ratings))
        self.assertEqual(next(row for row in ratings if row["id"] == "id_rating_fitch")["direction"],
                         "deteriorating")


class IpoContractTests(unittest.TestCase):
    def test_idx_universe_preserves_listing_timestamp(self):
        listing_ts = int(time.time()) - 86400
        row = universe._price_only_row({
            "sector": "technology", "ticker": "NEWX", "name": "New Company",
            "source_symbol": "NEWX.JK", "exchange": "IDX", "country": "ID",
            "listing_ts": listing_ts,
        }, universe.IDX_ALL_UNIVERSE)
        self.assertEqual(row.get("listing_ts"), listing_ts)

    def test_spac_detection(self):
        row = ipos._nasdaq_row({
            "proposedTickerSymbol": "TESTU",
            "companyName": "Test Acquisition Corp",
            "proposedExchange": "NASDAQ Global",
            "pricedDate": "7/16/2026",
        }, "priced")
        self.assertTrue(row["is_spac"])
        self.assertTrue(ipos._is_spac("Jones Ventures INTL Acquisition1 Corp", "JONEU"))
        self.assertTrue(ipos._is_spac("Columbus Circle Capital Corp III", "CCCTU"))
        self.assertFalse(ipos._is_spac("SK hynix Inc.", "SKHY"))

    def test_recent_idx_listing_proxy(self):
        sectors = [{"name": "Technology", "constituents": [{
            "country": "ID", "ticker": "NEWX", "name": "New Company",
            "listing_ts": int(time.time()) - 86400,
            "source_url": "https://www.tradingview.com/symbols/IDX-NEWX/",
        }]}]
        self.assertEqual(ipos._idx_recent(sectors)[0]["ticker"], "NEWX")

    def test_recent_idx_keeps_industry_for_compact_card(self):
        sectors = [{"name": "Entertainment, Media & Consumer Services", "constituents": [{
            "country": "ID", "ticker": "RANS", "name": "Rans Entertainment",
            "industry": "Entertainment & Movie Production",
            "listing_ts": int(time.time()) - 86400,
        }]}]
        self.assertEqual(ipos._idx_recent(sectors)[0]["industry"],
                         "Entertainment & Movie Production")

    def test_ipo_synthesis_is_view_specific_and_source_grounded(self):
        payload = {
            "upcoming_id": [{"ticker": "NEXT", "name": "Next Tbk", "industry": "Banks"}],
            "upcoming_us": [], "pipeline_id": [], "pipeline_us": [],
            "recent_id": [{"ticker": "RANS", "name": "Rans Tbk",
                           "industry": "Entertainment & Movie Production"}],
            "recent_us": [], "sp500_changes": [],
        }
        synthesis = ipos._deterministic_synthesis(payload)
        self.assertIn("NEXT", synthesis["upcoming"]["indonesia"])
        self.assertIn("RANS", synthesis["recent"]["indonesia"])
        self.assertIn("no verified", synthesis["upcoming"]["us"].lower())

    def test_ipo_synthesis_reuses_unchanged_cached_copy(self):
        payload = {key: [] for key in (
            "upcoming_id", "upcoming_us", "pipeline_id", "pipeline_us",
            "recent_id", "recent_us", "sp500_changes")}
        signature = ipos._synthesis_signature(payload)
        cached = ipos._deterministic_synthesis(payload)
        result, actual_signature = ipos._compile_synthesis(
            payload, {"synthesis_signature": signature, "synthesis": cached},
            summarize=lambda *_args: self.fail("unchanged IPO synthesis should not call the LLM"))
        self.assertEqual(result, cached)
        self.assertEqual(actual_signature, signature)

    def test_ipo_synthesis_truncation_keeps_complete_sentence(self):
        value = "S&P changes include " + ("a very long company description " * 30)
        trimmed = ipos._trim_sentence(value, 120)
        self.assertLessEqual(len(trimmed), 121)
        self.assertTrue(trimmed.endswith("."))
        self.assertFalse(trimmed.endswith(" ."))

    def test_eipo_company_first_layout(self):
        rows = ipos._parse_eipo_markdown("""
### PT Example Indonesia Tbk (EXAM)

Waiting For Offering

##### Periode Book Building

20 Juli 2026 - 02 Agustus 2026

##### Rentang Harga Book Building

Rp 120 - Rp 160

##### Sektor

Technology

[Prospektus](https://www.e-ipo.co.id/id/pipeline/get-propectus-file?id=999)
""")
        self.assertEqual(rows[0]["ticker"], "EXAM")
        self.assertEqual(rows[0]["status"], "waiting for offering")
        self.assertEqual(rows[0]["price"], "120 - Rp 160")
        self.assertEqual(rows[0]["currency"], "IDR")
        self.assertEqual(rows[0]["price_status"], "range")
        self.assertEqual(rows[0]["sector"], "Technology")
        self.assertIn("get-propectus-file", rows[0]["prospectus_url"])

    def test_eipo_closed_listing_can_enrich_recent_idx(self):
        official = ipos._parse_eipo_markdown("""
### PT Example Indonesia Tbk (EXAM)
Closed
##### Sektor
Technology
##### Tanggal Pencatatan
10 Jul 2026
##### Harga Final
Rp 170
##### Saham Ditawarkan
25.250.000 Lot
""", include_closed=True)
        scanner = [{
            "market": "ID", "kind": "ipo", "status": "listed", "ticker": "EXAM",
            "name": "Example Indonesia", "exchange": "IDX", "event_ts": official[0]["event_ts"] - 86400,
            "industry": "Packaged Software", "source": "TradingView first observed bar",
        }]
        merged = ipos._merge_idx_recent(scanner, official)
        self.assertEqual(merged[0]["event_ts"], official[0]["event_ts"])
        self.assertEqual(merged[0]["confidence"], "official_calendar")
        self.assertEqual(merged[0]["industry"], "Packaged Software")
        self.assertEqual(merged[0]["price"], "170")
        self.assertEqual(merged[0]["price_status"], "final")

    def test_nasdaq_filed_row_is_not_a_scheduled_listing(self):
        row = ipos._nasdaq_row({
            "proposedTickerSymbol": "FUTR", "companyName": "Future Company Inc.",
            "filedDate": "7/15/2026", "dollarValueOfSharesOffered": "$100,000,000",
        }, "filed")
        self.assertEqual(row["status"], "filed")
        self.assertEqual(row["date_type"], "filed_date")
        self.assertIn("sec.gov/edgar/browse", row["official_filing_url"])
        self.assertEqual(row["currency"], "USD")
        self.assertEqual(row["price_status"], "undisclosed")

    def test_cached_ipo_prices_get_currency_and_status_metadata(self):
        rows = [
            {"market": "US", "status": "priced", "price": "$18.00"},
            {"market": "US", "status": "expected", "price": "$14 - $16"},
            {"market": "ID", "status": "listed", "price": "170"},
            {"market": "ID", "status": "registered", "price": None},
        ]
        ipos._normalize_price_metadata(rows)
        self.assertEqual([(row["currency"], row["price_status"]) for row in rows], [
            ("USD", "final"), ("USD", "range"), ("IDR", "final"), ("IDR", "undisclosed"),
        ])

    def test_reported_idx_pipeline_requires_a_named_issuer(self):
        self.assertFalse(ipos._specific_id_pipeline_report(
            "BEI: Empat Perusahaan Siap IPO"))
        self.assertFalse(ipos._specific_id_pipeline_report(
            "5 Calon Emiten Siap IPO Bulan Depan, Ini Daftarnya"))
        self.assertFalse(ipos._specific_id_pipeline_report(
            "Pipeline IPO BEI Jadi Empat Perusahaan"))
        self.assertTrue(ipos._specific_id_pipeline_report(
            "PT Example Indonesia Tbk berencana IPO di BEI"))
        self.assertTrue(ipos._specific_id_pipeline_report(
            "Fore Coffee bersiap IPO tahun ini"))

    def test_generic_cached_pipeline_reports_are_removed(self):
        now = int(time.time())
        rows, health = ipos._reported_id_pipeline({
            "id_pipeline_asof": now,
            "pipeline_id_reported": [{
                "name": "Empat Perusahaan Siap IPO",
                "status": "reported pipeline",
            }, {
                "name": "PT Example Indonesia Tbk siap IPO",
                "status": "reported pipeline",
            }],
        }, [], [])
        self.assertEqual(health, "cached")
        self.assertEqual([row["name"] for row in rows],
                         ["PT Example Indonesia Tbk siap IPO"])

    def test_sp500_announcements_are_deduplicated_by_title(self):
        title = "Example Co Set to Join S&P 500 - S&P Global"
        rows = ipos._sp500_changes([{
            "title": title, "ts": 10, "url": "https://example.com/a", "source": "S&P Global",
        }, {
            "title": title, "ts": 10, "url": "https://example.com/b", "source": "S&P Global",
        }])
        self.assertEqual(len(rows), 1)

    def test_us_recent_ipo_gets_verified_nasdaq_industry(self):
        rows = [{"ticker": "NEWX", "name": "New Company", "is_spac": False}]
        health = ipos._enrich_us_classification(rows, {"NEWX": {
            "sector": "Technology", "industry": "EDP Services",
        }})
        self.assertEqual(rows[0]["sector"], "Technology")
        self.assertEqual(rows[0]["industry"], "EDP Services")
        self.assertEqual(health["industry_classified"], 1)

    def test_nasdaq_blank_check_industry_is_filtered_as_spac(self):
        rows = [{"ticker": "TESTU", "name": "Test Holdings", "is_spac": False}]
        ipos._enrich_us_classification(rows, {"TESTU": {
            "sector": "Finance", "industry": "Blank Checks",
        }})
        self.assertTrue(rows[0]["is_spac"])

    def test_ksei_registration_parser_keeps_official_pdf(self):
        rows = ipos._parse_ksei_html('''<article class="box"><small><b>01 Juli 2026</b></small>
          <p>Penawaran Umum Perdana atas Saham PT Example Indonesia Tbk</p>
          <a href="/Announcement/Files/example.pdf">unduh</a></article>''')
        self.assertEqual(rows[0]["status"], "registered")
        self.assertTrue(rows[0]["official_filing_url"].endswith("example.pdf"))


class NewsQualityTests(unittest.TestCase):
    def test_crypto_story_overrides_broad_market_category(self):
        item = news_router._normalize_item({
            "title": "Bitcoin ETF inflows lift crypto market liquidity",
            "summary": "Bitcoin and Ethereum trading volumes increased.",
            "source": "CoinDesk",
            "category": "MARKETS_FINANCE",
        })
        self.assertEqual(item["category"], "CRYPTO")

    def test_central_bank_rate_story_stays_economy(self):
        item = news_router._normalize_item({
            "title": "Bank Indonesia holds interest rate as rupiah steadies",
            "summary": "The central bank kept policy unchanged after its meeting.",
            "source": "Reuters",
            "category": "MARKETS_FINANCE",
            "query": "Indonesia stocks and banks",
        })
        self.assertEqual(item["category"], "ECONOMY")

    def test_syndicated_duplicate_titles_collapse(self):
        items = [{"title": "Bank Indonesia holds rates as rupiah steadies", "url": "https://a.example/1"},
                 {"title": "Bank Indonesia holds rates as rupiah steadies", "url": "https://b.example/2"}]
        self.assertEqual(len(news_router._dedupe(items, 10)), 1)

    def test_off_sector_story_is_rejected(self):
        sector = {"key": "renewables", "name": "Renewables", "constituents": []}
        item = {"title": "YouTube creator reaches ten million subscribers",
                "summary": "The entertainment channel expanded its audience.", "source": "Media News"}
        self.assertFalse(news_router._sector_relevant(item, sector))


class ResearchContractTests(unittest.TestCase):
    def test_curated_workbook_library_is_complete_and_source_linked(self):
        reports = research._curated()
        self.assertEqual(len(reports), 98)
        self.assertTrue(all(item.get("source_url") for item in reports))
        self.assertTrue(any(item.get("geography") == "Indonesia" for item in reports))
        self.assertTrue(all(item.get("geography") in research.REGIONS for item in reports))
        self.assertTrue(all(item.get("category") in research.REPORT_TYPES for item in reports))

    def test_research_region_contract_is_four_clear_buckets(self):
        cases = {
            "Indonesia / ASEAN": "Indonesia",
            "Southeast Asia": "SEA",
            "ASEAN+3": "APAC",
            "Asia-Pacific": "APAC",
            "United States / Global": "Global",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(research._region(raw), expected)

    def test_report_type_detects_economics_and_company_research(self):
        self.assertEqual(research._report_type({"title": "Indonesia Economic Outlook"}),
                         "Economics & Macro")
        self.assertEqual(research._report_type({"title": "BBCA Company Update", "ticker_tags": ["BBCA"]}),
                         "Equity Research")

    def test_exact_idx_ticker_and_company_name_are_tagged(self):
        tickers = {"BBCA", "TLKM"}
        names = [("BBCA", "bank central asia"), ("TLKM", "telkom indonesia")]
        self.assertEqual(research._ticker_tags("BBCA Company Update", tickers, names), ["BBCA"])
        self.assertEqual(research._ticker_tags("Telkom Indonesia Equity Research", tickers, names), ["TLKM"])

    def test_cached_collect_merges_without_duplicate_reports(self):
        previous = {
            "discovery_as_of": research._now(),
            "reports": [{
                "id": "live-test", "title": "BBCA Company Update", "publisher": "Test Broker",
                "source_url": "https://example.com/bbca", "landing_url": "https://example.com/bbca",
                "source_type": "official_discovery", "published_ts": research._now(),
                "ticker_tags": ["BBCA"], "category": "Public Markets", "geography": "Indonesia",
            }, {
                "id": "live-test-duplicate", "title": "BBCA Company Update", "publisher": "Test Broker",
                "source_url": "https://example.com/bbca", "source_type": "official_discovery",
                "published_ts": research._now(), "ticker_tags": ["BBCA"],
            }],
            "health": {"source_counts": {"Test Broker": 1}},
        }
        payload = research.collect([], previous)
        self.assertEqual(sum(item.get("source_url") == "https://example.com/bbca"
                             for item in payload["reports"]), 1)
        self.assertEqual(payload["health"]["discovery"], "cached")
        matched = next(item for item in payload["reports"] if item.get("source_url") == "https://example.com/bbca")
        self.assertEqual(matched["category"], "Equity Research")
        self.assertEqual(matched["geography"], "Indonesia")


class IdxClassificationTests(unittest.TestCase):
    def test_industry_groups_are_unambiguous(self):
        total = sum(len(values) for values in idx_membership.INDUSTRY_GROUPS.values())
        self.assertEqual(total, len(idx_membership.INDUSTRY_TO_COCKPIT))

    def test_industry_rules_override_broad_provider_sector(self):
        cases = {
            "Agricultural Commodities/Milling": "consumer",
            "Textiles": "consumer",
            "Containers/Packaging": "infrastructure",
            "Construction Materials": "infrastructure",
            "Life/Health Insurance": "financials",
            "Medical Distributors": "healthcare",
            "Movies/Entertainment": "entertainment",
            "Real Estate Development": "property",
            "Marine Shipping": "logistics",
        }
        for industry, expected in cases.items():
            with self.subTest(industry=industry):
                self.assertEqual(idx_membership._sector_key("Process Industries", industry), expected)

    def test_rans_uses_official_entertainment_classification(self):
        self.assertEqual(idx_membership._industry_for("RANS", "Miscellaneous Commercial Services"),
                         "Entertainment & Movie Production")
        self.assertEqual(idx_membership._sector_for(
            "RANS", "Commercial Services", "Entertainment & Movie Production"), "entertainment")


if __name__ == "__main__":
    unittest.main()
