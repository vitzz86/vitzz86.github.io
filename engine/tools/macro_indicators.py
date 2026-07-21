"""Verified Indonesia macro releases for the Project Cockpit dashboard.

Market prices and rates live in market telemetry. This module intentionally
contains only official macro releases, with explicit prior-period and benchmark
context where the source publishes it. Missing comparisons are never inferred.
"""
from __future__ import annotations

import copy
import datetime as dt
import math
import statistics


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


def _number(value) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _series(row: dict | None) -> list[float]:
    values = []
    for raw in (row or {}).get("spark") or []:
        value = _number(raw)
        if value is not None and value > 0:
            values.append(value)
    return values


def _period_move(values: list[float], sessions: int) -> float | None:
    if len(values) < 2:
        return None
    start = values[max(0, len(values) - sessions - 1)]
    return ((values[-1] / start) - 1) * 100 if start else None


def _realized_vol(values: list[float], sessions: int) -> float | None:
    sample = values[-(sessions + 1):]
    if len(sample) < 10:
        return None
    returns = [math.log(sample[i] / sample[i - 1]) for i in range(1, len(sample))
               if sample[i] > 0 and sample[i - 1] > 0]
    if len(returns) < 9:
        return None
    return statistics.stdev(returns) * math.sqrt(252) * 100


def _max_drawdown(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    peak = values[0]
    worst = 0.0
    for value in values[1:]:
        peak = max(peak, value)
        worst = min(worst, ((value / peak) - 1) * 100)
    return worst


def _market_source(row: dict | None) -> tuple[str, str]:
    row = row or {}
    url = str(row.get("url") or "")
    name = str(row.get("source_name") or "")
    if not name:
        name = "TradingView" if "tradingview" in url.lower() else "Yahoo Finance"
    return name, url


def _risk_card(identifier: str, pillar: str, label: str, value: str, period: str,
               source_row: dict, signal: str, direction: str, commentary: str, *,
               previous: str = "", comparison_label: str = "Reference",
               change: str = "", benchmark: str = "", secondary: list[str] | None = None,
               priority: int = 0) -> dict:
    source_name, source_url = _market_source(source_row)
    card = _indicator(
        identifier, pillar, label, value, period, "30-minute snapshot",
        source_name, source_url, signal, direction, commentary,
        previous=previous, comparison_label=comparison_label, change=change,
        benchmark=benchmark, secondary=secondary, priority=priority,
    )
    card.update({
        "published": "",
        "update_mode": "market_derived",
        "verification": "derived_from_market_source",
    })
    return card


def _country_risk(telemetry_by_symbol: dict[str, dict]) -> list[dict]:
    """Build transparent market-priced risk measures without estimating CDS/EMBI."""
    cards = []
    id10 = telemetry_by_symbol.get("ID10Y")
    us10 = telemetry_by_symbol.get("^TNX")
    if id10 and _number(id10.get("value")) is not None:
        value = _number(id10.get("value"))
        prev = _number(id10.get("prev_close"))
        move_bp = (value - prev) * 100 if prev is not None else None
        direction = "deteriorating" if move_bp is not None and move_bp > 10 else (
            "improving" if move_bp is not None and move_bp < -10 else "stable")
        signal = "red" if direction == "deteriorating" else (
            "green" if direction == "improving" else "neutral")
        cards.append(_risk_card(
            "id_risk_sbn10y", "Sovereign Funding", "Indonesia 10Y SBN Yield",
            f"{value:.2f}%", "Latest market snapshot", id10, signal, direction,
            "The benchmark rupiah sovereign yield is a funding-cost indicator, not a standalone default-risk measure.",
            previous=f"{prev:.2f}%" if prev is not None else "",
            change=f"{move_bp:+.1f}bp" if move_bp is not None else "", priority=10,
        ))
        if us10 and _number(us10.get("value")) is not None:
            us_value = _number(us10.get("value"))
            gap_bp = (value - us_value) * 100
            prev_us = _number(us10.get("prev_close"))
            previous_gap = ((prev - prev_us) * 100
                            if prev is not None and prev_us is not None else None)
            change_bp = gap_bp - previous_gap if previous_gap is not None else None
            gap_direction = "deteriorating" if change_bp is not None and change_bp > 10 else (
                "improving" if change_bp is not None and change_bp < -10 else "stable")
            gap_signal = "red" if gap_direction == "deteriorating" else (
                "green" if gap_direction == "improving" else "neutral")
            cards.append(_risk_card(
                "id_risk_yield_gap", "Risk Premium Proxy", "ID-US 10Y Yield Differential",
                f"{gap_bp:+.0f}bp", "Latest market snapshot", id10,
                gap_signal, gap_direction,
                "This carry and funding differential includes inflation and FX compensation; it is not a pure sovereign default spread.",
                previous=f"{previous_gap:+.0f}bp" if previous_gap is not None else "",
                change=f"{change_bp:+.1f}bp" if change_bp is not None else "",
                benchmark=f"US 10Y {us_value:.2f}%", secondary=["Not CDS or JPM EMBI"], priority=11,
            ))

    fx = telemetry_by_symbol.get("USDIDR=X")
    fx_values = _series(fx)
    fx_move_1m = _period_move(fx_values, 22)
    fx_move_3m = _period_move(fx_values, 66)
    if fx and fx_move_1m is not None:
        direction = "deteriorating" if fx_move_1m > 2 else (
            "improving" if fx_move_1m < -2 else "stable")
        signal = "red" if direction == "deteriorating" else (
            "green" if direction == "improving" else "neutral")
        cards.append(_risk_card(
            "id_risk_rupiah_move", "Currency Risk", "Rupiah 1M Move",
            f"{fx_move_1m:+.2f}%", "22 trading sessions", fx, signal, direction,
            "A positive USD/IDR move means rupiah depreciation; persistent weakening raises imported-inflation and foreign-flow risk.",
            benchmark=f"3M {fx_move_3m:+.2f}%" if fx_move_3m is not None else "",
            secondary=["Positive = IDR weaker"], priority=20,
        ))
    fx_vol_1m = _realized_vol(fx_values, 22)
    fx_vol_3m = _realized_vol(fx_values, 66)
    if fx and fx_vol_1m is not None:
        ratio = fx_vol_1m / fx_vol_3m if fx_vol_3m else 1
        direction = "deteriorating" if ratio > 1.15 else (
            "improving" if ratio < .85 else "stable")
        signal = "red" if direction == "deteriorating" else (
            "green" if direction == "improving" else "neutral")
        cards.append(_risk_card(
            "id_risk_fx_vol", "Currency Risk", "USD/IDR Realized Volatility",
            f"{fx_vol_1m:.2f}% ann.", "1M daily window", fx, signal, direction,
            "Annualized daily volatility measures rupiah instability; it complements, but does not replace, sovereign-spread data.",
            benchmark=f"3M {fx_vol_3m:.2f}% ann." if fx_vol_3m is not None else "",
            priority=21,
        ))

    jci = telemetry_by_symbol.get("^JKSE")
    jci_values = _series(jci)
    jci_vol_1m = _realized_vol(jci_values, 22)
    jci_vol_3m = _realized_vol(jci_values, 66)
    if jci and jci_vol_1m is not None:
        ratio = jci_vol_1m / jci_vol_3m if jci_vol_3m else 1
        direction = "deteriorating" if ratio > 1.15 else (
            "improving" if ratio < .85 else "stable")
        signal = "red" if direction == "deteriorating" else (
            "green" if direction == "improving" else "neutral")
        cards.append(_risk_card(
            "id_risk_jci_vol", "Equity Risk", "JCI Realized Volatility",
            f"{jci_vol_1m:.2f}% ann.", "1M daily window", jci, signal, direction,
            "Annualized JCI volatility tracks market stress and position-sizing risk rather than fundamental value.",
            benchmark=f"3M {jci_vol_3m:.2f}% ann." if jci_vol_3m is not None else "",
            priority=30,
        ))
    drawdown = _max_drawdown(jci_values)
    if jci and drawdown is not None:
        direction = "deteriorating" if drawdown <= -15 else (
            "improving" if drawdown > -5 else "stable")
        signal = "red" if direction == "deteriorating" else (
            "green" if direction == "improving" else "neutral")
        cards.append(_risk_card(
            "id_risk_jci_drawdown", "Equity Risk", "JCI 6M Max Drawdown",
            f"{drawdown:.2f}%", "6M daily window", jci, signal, direction,
            "Peak-to-trough loss shows realized equity stress within the available six-month history.",
            benchmark="Stress threshold -15%", priority=31,
        ))
    return cards


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
    country_risk = _country_risk(telemetry_by_symbol)
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
        "country_risk": country_risk,
        "health": {
            "official_indicator_count": len(all_official),
            "official_source_count": len({item["source_name"] for item in all_official}),
            "stale_official_count": stale_official,
            "country_risk_measure_count": len(country_risk),
            "country_risk_missing": [
                name for symbol, name in (("ID10Y", "Indonesia 10Y SBN"),)
                if symbol not in telemetry_by_symbol
            ],
        },
        "refresh_policy": (
            "Markets refresh every 30 minutes. Official macro cards advance only after a newer "
            "release is source-checked; release periods are shown on every card."
        ),
        "methodology_note": (
            "Direction compares only published periods or stated benchmarks. Green means improving, "
            "red means deteriorating, and grey means stable, mixed, or insufficient trend evidence."
        ),
        "country_risk_note": (
            "Market-priced risk measures use transparent 30-minute telemetry and daily price history. "
            "The ID-US yield differential is a carry/funding proxy, not CDS or JPM EMBI. Proprietary "
            "sovereign spreads and unavailable flow data are omitted rather than estimated."
        ),
    }
