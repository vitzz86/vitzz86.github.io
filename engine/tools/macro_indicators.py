"""Verified Indonesia macro releases for the Project Cockpit dashboard.

Market prices and rates live in market telemetry. This module intentionally
contains only official macro releases, with explicit prior-period and benchmark
context where the source publishes it. Missing comparisons are never inferred.
"""
from __future__ import annotations

import copy
import datetime as dt


DATA_CUTOFF = "2026-07-21"
STALE_DAYS = {"Daily": 4, "Monthly": 55, "Quarterly": 140,
              "Semiannual": 230, "Annual": 400, "Per review": 400,
              "Per meeting": 75}


def _indicator(identifier: str, pillar: str, label: str, value: str, period: str,
               frequency: str, source_name: str, source_url: str, signal: str,
               direction: str, commentary: str, *, previous: str = "",
               comparison_label: str = "Previous", change: str = "",
               benchmark: str = "", secondary: list[str] | None = None,
               published: str = "", priority: int = 0) -> dict:
    return {
        "id": identifier,
        "priority": priority,
        "pillar": pillar,
        "label": label,
        "value_display": value,
        "reference_period": period,
        "previous_display": previous,
        "comparison_label": comparison_label,
        "change_display": change,
        "benchmark_display": benchmark,
        "secondary": secondary or [],
        "frequency": frequency,
        "risk": signal,
        "direction": direction,
        "commentary": commentary,
        "source_name": source_name,
        "source_url": source_url,
        "published": published,
        "update_mode": "official_release",
        "verification": "official_source",
    }


CORE = [
    _indicator(
        "id_gdp", "Growth", "Real GDP Growth", "5.61% YoY", "Q1 2026",
        "Quarterly", "BPS",
        "https://www.bps.go.id/en/pressrelease/2026/05/05/2575/ekonomi-indonesia-triwulan-i-2026-tumbuh-5-61-persen--y-on-y-.html",
        "neutral", "mixed",
        "Annual growth is firm, but the quarter contracted and government consumption was a major driver.",
        benchmark="-0.77% QoQ", comparison_label="Sequential", published="2026-05-05", priority=1,
    ),
    _indicator(
        "id_pmi", "Growth", "PMI-BI Manufacturing", "51.43", "Q2 2026",
        "Quarterly", "Bank Indonesia",
        "https://www.bi.go.id/en/publikasi/ruang-media/news-release/Pages/sp_2813926.aspx",
        "neutral", "stable",
        "Manufacturing remains above the 50 expansion threshold; the next-quarter expectation is stronger.",
        benchmark="52.32", comparison_label="Q3 expectation", published="2026-07-17", priority=2,
    ),
    _indicator(
        "id_consumer_confidence", "Households", "Consumer Confidence", "117.8", "Jun 2026",
        "Monthly", "Bank Indonesia",
        "https://www.bi.go.id/en/publikasi/ruang-media/news-release/Default.aspx",
        "neutral", "stable",
        "Consumers remain optimistic, but the level alone does not establish improvement from May.",
        benchmark="Above 100 = optimistic", published="2026-07-10", priority=5,
    ),
    _indicator(
        "id_retail", "Households", "Retail Sales Index", "221.6 expected", "Jun 2026",
        "Monthly", "Bank Indonesia",
        "https://www.bi.go.id/en/publikasi/ruang-media/news-release/Pages/sp_2813426.aspx",
        "red", "deteriorating",
        "The expected index remains high, but the monthly contraction points to softer near-term spending.",
        change="-0.8% MoM", comparison_label="Monthly change", published="2026-07-14", priority=4,
    ),
    _indicator(
        "id_inflation", "Prices", "Headline CPI Inflation", "3.34% YoY", "Jun 2026",
        "Monthly", "BPS",
        "https://www.bps.go.id/en/pressrelease/2026/07/01/2590/inflasi-year-on-year--y-on-y--pada-juni-2026-sebesar-3-34-persen-.html",
        "red", "deteriorating",
        "Headline inflation accelerated and is close to the upper edge of Bank Indonesia's target corridor.",
        previous="3.08% YoY", change="+0.26pp", benchmark="BI target 1.5%-3.5%",
        published="2026-07-01", priority=6,
    ),
    _indicator(
        "id_core_inflation", "Prices", "Core Inflation", "2.76% YoY", "Jun 2026",
        "Monthly", "Bank Indonesia",
        "https://www.bi.go.id/en/publikasi/ruang-media/news-release/Pages/sp_2812926.aspx",
        "neutral", "rising",
        "Core inflation rose but remains inside the policy target corridor, indicating contained underlying pressure.",
        previous="2.59% YoY", change="+0.17pp", benchmark="BI target 1.5%-3.5%",
        published="2026-07-01", priority=7,
    ),
    _indicator(
        "id_food_inflation", "Prices", "Volatile Food Inflation", "5.58% YoY", "Jun 2026",
        "Monthly", "Bank Indonesia",
        "https://www.bi.go.id/en/publikasi/ruang-media/news-release/Pages/sp_2812926.aspx",
        "neutral", "improving",
        "Food inflation eased from May, although its level remains high enough to pressure household purchasing power.",
        previous="6.24% YoY", change="-0.66pp", benchmark="0.14% MoM",
        published="2026-07-01", priority=8,
    ),
    _indicator(
        "id_administered_inflation", "Prices", "Administered-Price Inflation", "3.42% YoY", "Jun 2026",
        "Monthly", "Bank Indonesia",
        "https://www.bi.go.id/en/publikasi/ruang-media/news-release/Pages/sp_2812926.aspx",
        "red", "deteriorating",
        "Regulated-price inflation accelerated sharply as non-subsidised fuel and airfares increased.",
        previous="2.07% YoY", change="+1.35pp", benchmark="1.41% MoM",
        published="2026-07-01", priority=9,
    ),
    _indicator(
        "id_bi_rate", "Monetary", "BI Policy Rate", "5.75%", "18 Jun 2026",
        "Per meeting", "Bank Indonesia",
        "https://www.bi.go.id/en/statistik/indikator/bi-rate.aspx",
        "neutral", "stable",
        "The higher policy setting supports rupiah stability while raising domestic funding and valuation hurdles.",
        previous="5.50%", change="+25bp", benchmark="Real rate +2.41pp vs CPI",
        published="2026-06-18", priority=10,
    ),
    _indicator(
        "id_reserves", "External", "FX Reserves", "US$145.6bn", "Jun 2026",
        "Monthly", "Bank Indonesia",
        "https://www.bi.go.id/en/publikasi/ruang-media/news-release/Pages/sp_2813126.aspx",
        "neutral", "stable",
        "Reserve cover remains adequate; the key watch is whether rupiah defence causes persistent drawdowns.",
        benchmark="5.5 months of imports", published="2026-07-07", priority=11,
    ),
    _indicator(
        "id_trade", "External", "Trade Balance", "-US$1.61bn", "May 2026",
        "Monthly", "BPS",
        "https://www.bps.go.id/en/pressrelease/2026/07/01/2587/ekspor-dan-impor-indonesia-mei-2026-masing-masing-tercatat-usd-23-20-miliar-dan-usd-24-81-miliar.html",
        "red", "deteriorating",
        "The monthly deficit weakens near-term FX support even though the year-to-date balance remains positive.",
        benchmark="Jan-May +US$4.03bn", secondary=["Exports US$23.20bn", "Imports US$24.81bn"],
        published="2026-07-01", priority=12,
    ),
    _indicator(
        "id_current_account", "External", "Current Account", "-US$4.0bn", "Q1 2026",
        "Quarterly", "Bank Indonesia",
        "https://www.bi.go.id/en/publikasi/ruang-media/news-release/Pages/sp_2810926.aspx",
        "red", "deteriorating",
        "The deficit is manageable but increases dependence on direct and portfolio investment inflows.",
        benchmark="-1.1% of GDP", secondary=["Overall BOP -US$9.1bn"],
        published="2026-05-22", priority=13,
    ),
    _indicator(
        "id_apbn", "Fiscal", "APBN Deficit", "Rp196.5tn", "H1 2026",
        "Monthly", "Ministry of Finance",
        "https://www.kemenkeu.go.id/informasi-publik/publikasi/siaran-pers/APBN-2026-Tetap-Sehat-Dukung-Pertumbuhan-Ekonomi",
        "neutral", "stable",
        "The first-half deficit is contained, while the full-year outlook is close enough to the legal ceiling to monitor.",
        benchmark="0.76% GDP; FY outlook 2.85%", published="2026-07-20", priority=14,
    ),
    _indicator(
        "id_credit_npl", "Financial System", "Credit Growth / Gross NPL", "9.98% / 2.17%", "Apr 2026",
        "Monthly", "OJK",
        "https://iru.ojk.go.id/iru/WebSite/ArticleList/View/1014_May_2026_Board_of_Commissioners_Meeting%3A_Financial_Services_Sector_Stability_Maintained_Amid_Increasing_Pressures_on_Global_Economic_Performance",
        "neutral", "stable",
        "Lending is expanding while headline asset quality remains contained.",
        benchmark="Net NPL 0.84%", secondary=["Loan at Risk 8.82%"],
        published="2026-06-02", priority=16,
    ),
]


DETAIL = [
    _indicator(
        "id_business_activity", "Growth", "Business Activity Survey", "WNB 12.97%", "Q2 2026",
        "Quarterly", "Bank Indonesia",
        "https://www.bi.go.id/en/publikasi/ruang-media/news-release/Pages/sp_2813826.aspx",
        "green", "improving", "The higher weighted net balance indicates broader business expansion.",
        previous="10.11%", change="+2.86pp", published="2026-07-16", priority=3,
    ),
    _indicator(
        "id_wholesale_prices", "Prices", "Wholesale Price Inflation", "6.51% YoY", "Jun 2026",
        "Monthly", "BPS",
        "https://www.bps.go.id/en/pressrelease/2026/07/01/2593/in-june-2026--the-national-wholesale-price-index--wpi--changed-by-6-51-percent-year-on-year-.html",
        "red", "deteriorating", "Upstream price pressure is elevated and may pass through to producer margins and consumer prices.",
        change="+0.83% MoM", benchmark="+4.94% YTD", published="2026-07-01", priority=9,
    ),
    _indicator(
        "id_external_debt", "External", "External Debt", "US$444.4bn", "May 2026",
        "Monthly", "Bank Indonesia",
        "https://www.bi.go.id/en/publikasi/ruang-media/news-release/Default.aspx",
        "neutral", "rising", "Currency mix and near-term refinancing needs matter more than the headline stock.",
        change="+2.1% YoY", published="2026-07-15", priority=12,
    ),
    _indicator(
        "id_fiscal_execution", "Fiscal", "Revenue / Spending", "Rp1,459.4tn / Rp1,656.0tn", "H1 2026",
        "Monthly", "Ministry of Finance",
        "https://www.kemenkeu.go.id/informasi-publik/publikasi/siaran-pers/APBN-2026-Tetap-Sehat-Dukung-Pertumbuhan-Ekonomi",
        "neutral", "mixed", "Revenue quality and productive spending composition determine the growth impact.",
        secondary=["Revenue +21.4% YoY", "Spending +17.8% YoY"],
        published="2026-07-20", priority=14,
    ),
    _indicator(
        "id_labour", "Labour", "Unemployment / Average Wage", "4.68% / Rp3.29m", "Feb 2026",
        "Semiannual", "BPS",
        "https://www.bps.go.id/en/pressrelease/2026/05/05/2574/tingkat-pengangguran-terbuka--tpt--sebesar-4-68-persen--rata-rata-upah-buruh-sebesar-3-29-juta-rupiah-.html",
        "green", "improving", "Unemployment improved, while real wage growth and formal-job quality remain the key checks.",
        benchmark="147.67m employed", published="2026-05-05", priority=15,
    ),
    _indicator(
        "id_asset_quality", "Financial System", "Net NPL / Loan at Risk", "0.84% / 8.82%", "Apr 2026",
        "Monthly", "OJK",
        "https://iru.ojk.go.id/iru/WebSite/ArticleList/View/1014_May_2026_Board_of_Commissioners_Meeting%3A_Financial_Services_Sector_Stability_Maintained_Amid_Increasing_Pressures_on_Global_Economic_Performance",
        "neutral", "stable", "Both arrears and broader restructured exposures should stay contained as credit expands.",
        published="2026-06-02", priority=17,
    ),
    _indicator(
        "id_bank_resilience", "Financial System", "CAR / LCR", "23.97% / 192.37%", "Apr 2026",
        "Monthly", "OJK",
        "https://iru.ojk.go.id/iru/WebSite/ArticleList/View/1014_May_2026_Board_of_Commissioners_Meeting%3A_Financial_Services_Sector_Stability_Maintained_Amid_Increasing_Pressures_on_Global_Economic_Performance",
        "neutral", "stable", "Capital and liquidity buffers remain comfortably above regulatory minimums.",
        published="2026-06-02", priority=18,
    ),
]


RATINGS = [
    _indicator(
        "id_rating_sp", "Sovereign Credit", "S&P Global", "BBB / Stable", "13 Jul 2026",
        "Per review", "Bank Indonesia / S&P Global",
        "https://www.bi.go.id/en/iru/highlight-news/Pages/-S%26P-Affirmed-Indonesia%E2%80%99s-Sovereign-Credit-Rating-at-BBB-with-Stable-Outlook.aspx",
        "neutral", "stable",
        "Indonesia remains investment grade. S&P expects the recent weakening in fiscal and external indicators to be temporary.",
        benchmark="Investment grade", comparison_label="Outlook", previous="Stable",
        published="2026-07-13", priority=1,
    ),
    _indicator(
        "id_rating_fitch", "Sovereign Credit", "Fitch Ratings", "BBB / Negative", "4 Mar 2026",
        "Per review", "Bank Indonesia / Fitch Ratings",
        "https://www.bi.go.id/en/iru/highlight-news/Pages/-Fitch-Affirms-the-Republic-of-Indonesia%E2%80%99s-Rating-at-BBB-and-Revises-Outlook-to-Negative.aspx",
        "red", "deteriorating",
        "The rating remains investment grade, but the negative outlook flags policy-consistency, fiscal, and external-buffer risks.",
        benchmark="Investment grade", comparison_label="Prior outlook", previous="Stable",
        change="Outlook cut to Negative", published="2026-03-04", priority=2,
    ),
    _indicator(
        "id_rating_moodys", "Sovereign Credit", "Moody's", "Baa2 / Negative", "5 Feb 2026",
        "Per review", "Bank Indonesia / Moody's",
        "https://www.bi.go.id/en/publikasi/ruang-media/news-release/Pages/sp_282726.aspx",
        "red", "deteriorating",
        "Moody's kept Indonesia one notch above its investment-grade floor while highlighting lower policy predictability.",
        benchmark="Investment grade", comparison_label="Prior outlook", previous="Stable",
        change="Outlook cut to Negative", published="2026-02-05", priority=3,
    ),
    _indicator(
        "id_classification_msci", "Market Classification", "MSCI Indonesia", "Emerging Market", "23 Jun 2026",
        "Annual", "MSCI",
        "https://ir.msci.com/news-releases/news-release-details/msci-announces-results-msci-2026-market-classification-review",
        "neutral", "monitoring",
        "Indonesia remains in MSCI's emerging-market universe, while shareholder transparency and coordinated-trading concerns remain under review.",
        benchmark="MSCI EM universe", comparison_label="Index coverage", previous="Large & mid cap",
        secondary=["Accessibility monitored"], published="2026-06-23", priority=4,
    ),
    _indicator(
        "id_classification_ftse", "Market Classification", "FTSE Russell", "Secondary Emerging", "Apr 2026",
        "Semiannual", "FTSE Russell",
        "https://www.lseg.com/content/dam/ftse-russell/en_us/documents/country-classification/ftse-country-classification-update-latest.pdf",
        "neutral", "monitoring",
        "FTSE Russell kept Indonesia at Secondary Emerging while monitoring transparency, free-float, governance, and market-integrity reforms.",
        benchmark="Classification unchanged", comparison_label="Watch list", previous="Not added",
        secondary=["Reforms monitored"], published="2026-04-07", priority=5,
    ),
]


def _mark_stale(rows: list[dict]) -> int:
    today = dt.datetime.now(dt.timezone.utc).date()
    stale_count = 0
    for item in rows:
        published = item.get("published")
        try:
            age = (today - dt.date.fromisoformat(str(published))).days
        except (TypeError, ValueError):
            item["stale"] = False
            continue
        item["stale"] = age > STALE_DAYS.get(item.get("frequency"), 120)
        item["age_days"] = max(0, age)
        stale_count += int(item["stale"])
    return stale_count


def collect(telemetry: list, previous: dict | None = None) -> dict:
    """Return official macro cards with explicit provenance and comparisons."""
    core = copy.deepcopy(CORE)
    detail = copy.deepcopy(DETAIL)
    ratings = copy.deepcopy(RATINGS)
    telemetry_by_symbol = {row.get("symbol"): row for row in telemetry or []}
    bi = telemetry_by_symbol.get("BI_RATE")
    if bi:
        card = next((item for item in core if item["id"] == "id_bi_rate"), None)
        if card:
            card["value_display"] = f"{float(bi.get('value') or 0):.2f}%"
            card["reference_period"] = bi.get("asof") or card["reference_period"]
            card["source_name"] = bi.get("source_name") or card["source_name"]
            card["source_url"] = bi.get("url") or card["source_url"]

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_official = core + detail + ratings
    stale_official = _mark_stale(all_official)
    return {
        "as_of": now,
        "data_cutoff": DATA_CUTOFF,
        "core": core,
        "detail": detail,
        "ratings": ratings,
        "health": {
            "official_indicator_count": len(all_official),
            "official_source_count": len({item["source_name"] for item in all_official}),
            "stale_official_count": stale_official,
        },
        "refresh_policy": (
            "Markets refresh every 30 minutes. Official macro cards advance only after a newer "
            "release is source-checked; release periods are shown on every card."
        ),
        "methodology_note": (
            "Direction compares only published periods or stated benchmarks. Green means improving, "
            "red means deteriorating, and grey means stable, mixed, or insufficient trend evidence."
        ),
    }
