"""Full IDX price-only universe via TradingView's Indonesia scanner.

IDX's public company-profile endpoints currently block non-browser access from
automation. TradingView's scanner gives us the practical feed shape we need for
the dashboard: current IDX tickers, company names, sectors, price, daily change,
volume, and market cap in one request. Rich fundamentals stay limited to the
curated scored universe; this module is intentionally breadth-first.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.request
from functools import lru_cache

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings

TV_SCAN_URL = "https://scanner.tradingview.com/indonesia/scan"
TV_SYMBOL = "https://www.tradingview.com/symbols/IDX-{ticker}/"

TV_COLUMNS = [
    "name",
    "description",
    "close",
    "change",
    "volume",
    "market_cap_basic",
    "sector",
    "industry",
    "exchange",
    "type",
    "Perf.W",
    "Perf.1M",
    "Perf.3M",
    "Perf.6M",
    "Perf.YTD",
    "Perf.Y",
    "Volatility.W",
    "Volatility.M",
    "Volatility.D",
    "average_volume_10d_calc",
    "average_volume_30d_calc",
    "relative_volume_10d_calc",
    "Value.Traded",
    "Recommend.All",
    "RSI",
    "first_bar_time",
]

TV_SECTOR_TO_COCKPIT = {
    "communications": "technology",
    "consumer durables": "consumer",
    "consumer non-durables": "consumer",
    "consumer services": "consumer",
    "distribution services": "consumer",
    "electronic technology": "technology",
    "energy minerals": "energy",
    "finance": "financials",
    "health services": "healthcare",
    "health technology": "healthcare",
    "industrial services": "infrastructure",
    "miscellaneous": "consumer",
    "non-energy minerals": "energy",
    "process industries": "energy",
    "producer manufacturing": "infrastructure",
    "retail trade": "consumer",
    "technology services": "technology",
    "transportation": "logistics",
    "utilities": "renewables",
}

INDUSTRY_GROUPS = {
    "financials": {
        "Finance/Rental/Leasing", "Financial Conglomerates", "Investment Banks/Brokers",
        "Investment Managers", "Life/Health Insurance", "Major Banks", "Multi-Line Insurance",
        "Property/Casualty Insurance", "Regional Banks",
    },
    "property": {
        "Homebuilding", "Real Estate Development", "Real Estate Investment Trusts",
    },
    "entertainment": {
        "Advertising/Marketing Services", "Broadcasting", "Cable/Satellite TV",
        "Hotels/Resorts/Cruise lines", "Movies/Entertainment", "Publishing: Newspapers",
        "Restaurants",
    },
    "logistics": {
        "Air Freight/Couriers", "Airlines", "Marine Shipping", "Other Transportation", "Trucking",
    },
    "technology": {
        "Aerospace & Defense", "Computer Peripherals", "Computer Processing Hardware",
        "Data Processing Services", "Electronic Components", "Electronic Production Equipment",
        "Electronics Distributors", "Information Technology Services", "Internet Software/Services", "Packaged Software",
        "Telecommunications Equipment", "Major Telecommunications", "Specialty Telecommunications",
        "Wireless Telecommunications",
    },
    "healthcare": {
        "Hospital/Nursing Management", "Medical Distributors", "Medical Specialties",
        "Medical/Nursing Services", "Pharmaceuticals: Major", "Pharmaceuticals: Other",
    },
    "renewables": {
        "Alternative Power Generation", "Electric Utilities",
    },
    "energy": {
        "Aluminum", "Chemicals: Agricultural", "Chemicals: Major Diversified",
        "Chemicals: Specialty", "Coal", "Gas Distributors", "Integrated Oil",
        "Oil & Gas Production", "Oil Refining/Marketing", "Other Metals/Minerals",
        "Precious Metals", "Steel",
    },
    "infrastructure": {
        "Building Products", "Commercial Printing/Forms", "Construction Materials",
        "Containers/Packaging", "Contract Drilling", "Electrical Products",
        "Engineering & Construction", "Environmental Services", "Forest Products",
        "Industrial Conglomerates", "Industrial Machinery", "Industrial Specialties",
        "Metal Fabrication", "Miscellaneous Manufacturing", "Office Equipment/Supplies",
        "Oilfield Services/Equipment", "Pulp & Paper", "Trucks/Construction/Farm Machinery",
    },
    "consumer": {
        "Agricultural Commodities/Milling", "Apparel/Footwear", "Apparel/Footwear Retail",
        "Auto Parts: OEM", "Automotive Aftermarket", "Beverages: Alcoholic", "Beverages: Non-Alcoholic",
        "Department Stores", "Drugstore Chains", "Electronics/Appliance Stores",
        "Electronics/Appliances", "Food Distributors", "Food Retail", "Food: Major Diversified",
        "Food: Meat/Fish/Dairy", "Food: Specialty/Candy", "Home Furnishings",
        "Home Improvement Chains", "Household/Personal Care", "Internet Retail", "Motor Vehicles",
        "Miscellaneous", "Miscellaneous Commercial Services", "Other Consumer Services",
        "Other Consumer Specialties", "Personnel Services",
        "Specialty Stores", "Textiles", "Tobacco", "Wholesale Distributors",
    },
}
INDUSTRY_TO_COCKPIT = {
    industry: sector for sector, industries in INDUSTRY_GROUPS.items() for industry in industries
}

INDUSTRY_HINTS = [
    ("property", ("real estate", "reit", "property development", "homebuilding")),
    ("entertainment", ("media", "broadcasting", "movies", "publishing", "advertising",
                       "restaurants", "hotels", "travel", "resorts", "gaming")),
    ("logistics", ("shipping", "airlines", "marine", "trucking", "logistics",
                   "transportation")),
    ("technology", ("software", "internet", "data processing", "telecom",
                    "semiconductor", "electronics")),
    ("healthcare", ("pharmaceutical", "hospital", "medical", "health")),
    ("financials", ("bank", "insurance", "finance", "securities", "investment")),
    ("renewables", ("electric utilities", "renewable", "geothermal", "solar", "power")),
]

IDX_SECTOR_OVERRIDES = {
    "ASII": "consumer",
    "ACES": "consumer",
    "SIDO": "healthcare",
    "CTRA": "property",
    "DMAS": "property",
    "BSDE": "property",
    "PWON": "property",
    "SMRA": "property",
    "TLKM": "technology",
    "ISAT": "technology",
    "EXCL": "technology",
    "MTEL": "infrastructure",
    "TOWR": "infrastructure",
    "TBIG": "infrastructure",
    "WIKA": "infrastructure",
    "WSKT": "infrastructure",
    "ADHI": "infrastructure",
    "PTPP": "infrastructure",
    "JSMR": "infrastructure",
    "BREN": "renewables",
    "PGEO": "renewables",
    "ESSA": "renewables",
    "AMMN": "energy",
    "ANTM": "energy",
    "INCO": "energy",
    "MDKA": "energy",
    "BYAN": "energy",
    "ADRO": "energy",
    "ITMG": "energy",
    "PTBA": "energy",
    # Provider classifications for diversified or newly listed companies can
    # be too broad. Keep exceptions explicit and reviewable.
    "RANS": "entertainment",
    "PNIN": "financials",
    "PNLF": "financials",
    "JIHD": "property",
    "KIJA": "property",
    "KPIG": "property",
    "PANI": "property",
    "BEST": "property",
    "GMFI": "infrastructure",
    "ERAA": "consumer",
    "ARCI": "energy",
    "BRPT": "energy",
    "GGRP": "energy",
    "TPIA": "energy",
    "CSAP": "consumer",
    "CMPP": "logistics",
    "EDGE": "technology",
    "INAF": "healthcare",
}

IDX_INDUSTRY_OVERRIDES = {
    "RANS": "Entertainment & Movie Production",
    "EDGE": "Data Center & Internet Services",
    "WIKA": "Engineering & Construction",
    "WSKT": "Engineering & Construction",
    "INAF": "Pharmaceuticals: Other",
    "CMPP": "Airlines",
}


def _num(raw) -> float | None:
    if raw is None:
        return None
    try:
        return float(str(raw).replace(",", "").replace("%", "").strip())
    except Exception:  # noqa: BLE001
        return None


def _fmt_idr(value: float | int | None) -> str:
    try:
        n = float(value or 0)
    except Exception:  # noqa: BLE001
        n = 0
    if n >= 1e15:
        return f"IDR {n / 1e15:.2f}Q"
    if n >= 1e12:
        return f"IDR {n / 1e12:.0f}T"
    if n >= 1e9:
        return f"IDR {n / 1e9:.0f}B"
    if n >= 1e6:
        return f"IDR {n / 1e6:.0f}M"
    return ""


def _tier_idr(value: float | int | None) -> str:
    try:
        n = float(value or 0)
    except Exception:  # noqa: BLE001
        n = 0
    if n >= 500_000_000_000_000:
        return "mega"
    if n >= 100_000_000_000_000:
        return "large"
    if n >= 10_000_000_000_000:
        return "mid"
    return "small"


def _clean_ticker(raw: str) -> str:
    ticker = str(raw or "").upper().strip()
    if ":" in ticker:
        ticker = ticker.split(":", 1)[1]
    return ticker.replace(".", "-")


def _sector_key(tv_sector: str | None, industry: str | None) -> str:
    exact = INDUSTRY_TO_COCKPIT.get(str(industry or "").strip())
    if exact:
        return exact
    blob = f"{tv_sector or ''} {industry or ''}".lower()
    for sector, hints in INDUSTRY_HINTS:
        if any(h in blob for h in hints):
            return sector
    return TV_SECTOR_TO_COCKPIT.get(str(tv_sector or "").strip().lower(), "consumer")


def _sector_for(ticker: str, tv_sector: str | None, industry: str | None) -> str:
    return IDX_SECTOR_OVERRIDES.get(ticker, _sector_key(tv_sector, industry))


def _industry_for(ticker: str, industry: str | None) -> str:
    return IDX_INDUSTRY_OVERRIDES.get(ticker, str(industry or "").strip())


def _classification_basis(ticker: str, industry: str | None) -> str:
    if ticker in IDX_SECTOR_OVERRIDES:
        return "ticker_override"
    if str(industry or "").strip() in INDUSTRY_TO_COCKPIT:
        return "industry_exact"
    return "provider_sector_fallback"


def _start_price(close: float | None, perf_pct: float | None) -> float | None:
    if close is None or perf_pct is None:
        return None
    base = 1 + perf_pct / 100
    if base <= 0:
        return None
    return close / base


def _interp(points: list[tuple[int, float | None]], length: int = 130) -> list[float]:
    clean = [(i, float(v)) for i, v in points if v is not None and v > 0]
    if len(clean) < 2:
        return []
    clean = sorted(dict(clean).items())
    out: list[float] = []
    for idx in range(length):
        left = clean[0]
        right = clean[-1]
        for a, b in zip(clean, clean[1:]):
            if a[0] <= idx <= b[0]:
                left, right = a, b
                break
        if right[0] == left[0]:
            val = right[1]
        else:
            pct = (idx - left[0]) / (right[0] - left[0])
            val = left[1] + (right[1] - left[1]) * pct
        out.append(round(val, 4))
    return out


def _checkpoint_spark(close: float | None, data: dict) -> list[float]:
    return _interp([
        (0, _start_price(close, _num(data.get("Perf.6M")))),
        (65, _start_price(close, _num(data.get("Perf.3M")))),
        (108, _start_price(close, _num(data.get("Perf.1M")))),
        (125, _start_price(close, _num(data.get("Perf.W")))),
        (129, close),
    ])


def _checkpoint_ts(length: int = 130) -> list[int]:
    today = _jakarta_now().replace(hour=15, minute=50, second=0, microsecond=0)
    return [int((today - dt.timedelta(days=(length - 1 - i))).timestamp()) for i in range(length)]


def _jakarta_now() -> dt.datetime:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("Asia/Jakarta"))
    except Exception:  # noqa: BLE001
        return dt.datetime.now(dt.timezone(dt.timedelta(hours=7)))


def idx_session_state() -> dict:
    """Lightweight fallback state for price-only IDX scanner rows.

    TradingView is authoritative for IDX quote rows. Scanner-only rows need a
    consistent session state so they do not all render as stale closed assets
    during the Jakarta session.
    """
    now = _jakarta_now()
    if now.weekday() >= 5:
        return {"open": False, "mkt_start": None, "mkt_end": None}
    sessions = (
        ((9, 0), (11, 30), (14, 0), (15, 50))
        if now.weekday() == 4
        else ((9, 0), (12, 0), (13, 30), (15, 50))
    )
    spans = []
    for start_hm, end_hm in ((sessions[0], sessions[1]), (sessions[2], sessions[3])):
        start = now.replace(hour=start_hm[0], minute=start_hm[1], second=0, microsecond=0)
        end = now.replace(hour=end_hm[0], minute=end_hm[1], second=0, microsecond=0)
        spans.append((start, end))
        if start <= now <= end:
            return {"open": True, "mkt_start": int(start.timestamp()), "mkt_end": int(end.timestamp())}
    return {
        "open": False,
        "mkt_start": int(spans[0][0].timestamp()),
        "mkt_end": int(spans[-1][1].timestamp()),
    }


@lru_cache(maxsize=1)
def scanner_rows(limit: int | None = None) -> list[dict]:
    limit = limit or int(getattr(settings, "IDX_ALL_PRICE_LIMIT", 1200))
    payload = {
        "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
        "options": {"lang": "en"},
        "markets": ["indonesia"],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": TV_COLUMNS,
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
        "range": [0, limit],
    }
    req = urllib.request.Request(
        TV_SCAN_URL,
        data=json.dumps(payload).encode(),
        headers={
            "User-Agent": "Mozilla/5.0 (Project Cockpit; IDX scanner)",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://www.tradingview.com",
            "Referer": "https://www.tradingview.com/",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as res:
                data = json.load(res)
            rows = data.get("data") or []
            print(f"[idx_membership] TradingView IDX scanner: {len(rows)}/{data.get('totalCount')} rows")
            return rows
        except Exception as exc:  # noqa: BLE001
            if attempt == 2:
                print(f"[idx_membership] TradingView IDX scanner failed: {exc}")
                return []
            time.sleep(1.0 * (attempt + 1))
    return []


def _parsed(row: dict) -> dict | None:
    vals = row.get("d") or []
    if len(vals) < len(TV_COLUMNS):
        return None
    data = dict(zip(TV_COLUMNS, vals))
    ticker = _clean_ticker(data.get("name") or row.get("s"))
    if not ticker:
        return None
    cap = _num(data.get("market_cap_basic"))
    volume = _num(data.get("volume")) or 0.0
    price = _num(data.get("close"))
    dp = _num(data.get("change"))
    industry = _industry_for(ticker, data.get("industry"))
    sector = _sector_for(ticker, data.get("sector"), industry)
    spark = _checkpoint_spark(price, data)
    meta = settings.COUNTRY_META["ID"]
    return {
        "ticker": ticker,
        "name": str(data.get("description") or ticker).strip(),
        "source_symbol": f"{ticker}.JK",
        "exchange": "IDX",
        "country": "ID",
        "mktcap": _fmt_idr(cap),
        "tier": _tier_idr(cap),
        "sector_key": sector,
        "sector": sector,
        "provider_sector_key": sector,
        "provider_sector_raw": data.get("sector") or "",
        "country_name": meta["name"],
        "country_flag": meta["flag"],
        "region": meta["region"],
        "market_cap_value": cap,
        "index_groups": ["idx_all"],
        "industry": industry,
        "sector_classification": _classification_basis(ticker, industry),
        "source_provider": "tradingview",
        "source_name": "TradingView",
        "source_url": TV_SYMBOL.format(ticker=ticker),
        "quote_asof": int(time.time()),
        "quote_mode": "near_realtime_snapshot",
        "value": price,
        "delta_pct": dp,
        "volume": volume,
        "avg_volume_10d": _num(data.get("average_volume_10d_calc")),
        "avg_volume_30d": _num(data.get("average_volume_30d_calc")),
        "relative_volume_10d": _num(data.get("relative_volume_10d_calc")),
        "turnover": _num(data.get("Value.Traded")) or round((price or 0.0) * volume, 0),
        "perf_1w": _num(data.get("Perf.W")),
        "perf_1m": _num(data.get("Perf.1M")),
        "perf_3m": _num(data.get("Perf.3M")),
        "perf_6m": _num(data.get("Perf.6M")),
        "perf_ytd": _num(data.get("Perf.YTD")),
        "perf_1y": _num(data.get("Perf.Y")),
        "volatility_1w": _num(data.get("Volatility.W")),
        "volatility_1m": _num(data.get("Volatility.M")),
        "volatility_1d": _num(data.get("Volatility.D")),
        "recommend_all": _num(data.get("Recommend.All")),
        "rsi": _num(data.get("RSI")),
        # TradingView's first observed daily bar is a practical listing-date
        # proxy for recent-IPO discovery. The IPO panel labels this provenance.
        "listing_ts": int(data["first_bar_time"]) if _num(data.get("first_bar_time")) else None,
        "spark": spark,
        "spark_ts": _checkpoint_ts(len(spark)) if spark else [],
        "price_history_quality": "tradingview_performance_checkpoints",
        "chart_quality": {
            "24h": "unavailable",
            "1W": "performance_checkpoint",
            "1M": "performance_checkpoint",
            "3M": "performance_checkpoint",
            "6M": "performance_checkpoint",
        },
    }


def idx_all_rows(rows: list[dict] | None = None) -> list[dict]:
    out = []
    for row in rows if rows is not None else scanner_rows():
        parsed = _parsed(row)
        if parsed:
            out.append(parsed)
    return out


def _parsed_rows(rows: list[dict] | None = None) -> list[dict]:
    if rows is not None and rows and ("d" not in rows[0]):
        return rows
    return idx_all_rows(rows)


def price_map(rows: list[dict] | None = None) -> dict[str, dict]:
    state = idx_session_state()
    prices = {}
    for row in _parsed_rows(rows):
        if row.get("value") is None:
            continue
        prices[row["source_symbol"]] = {
            "value": round(float(row["value"]), 4),
            "delta_pct": round(float(row.get("delta_pct") or 0.0), 2),
            "volume": float(row.get("volume") or 0.0),
            "turnover": float(row.get("turnover") or 0.0),
            "market_cap_value": row.get("market_cap_value"),
            "avg_volume_10d": row.get("avg_volume_10d"),
            "avg_volume_30d": row.get("avg_volume_30d"),
            "relative_volume_10d": row.get("relative_volume_10d"),
            "perf_1w": row.get("perf_1w"),
            "perf_1m": row.get("perf_1m"),
            "perf_3m": row.get("perf_3m"),
            "perf_6m": row.get("perf_6m"),
            "perf_ytd": row.get("perf_ytd"),
            "perf_1y": row.get("perf_1y"),
            "volatility_1w": row.get("volatility_1w"),
            "volatility_1m": row.get("volatility_1m"),
            "volatility_1d": row.get("volatility_1d"),
            "recommend_all": row.get("recommend_all"),
            "rsi": row.get("rsi"),
            "open": state["open"],
            "mkt_start": state["mkt_start"],
            "mkt_end": state["mkt_end"],
            "quote_asof": row.get("quote_asof") or int(time.time()),
            "quote_mode": row.get("quote_mode") or "near_realtime_snapshot",
            "spark": row.get("spark") or [],
            "spark_ts": row.get("spark_ts") or [],
            "intraday": [],
            "price_history_quality": row.get("price_history_quality"),
            "chart_quality": row.get("chart_quality") or {
                "24h": "unavailable",
                "1W": "performance_checkpoint",
                "1M": "performance_checkpoint",
                "3M": "performance_checkpoint",
                "6M": "performance_checkpoint",
            },
            "source": "tradingview_scanner",
        }
    return prices


def source_health(rows: list[dict] | None = None) -> dict:
    parsed = [r for r in _parsed_rows(rows)
              if r.get("country") == "ID" and r.get("source_provider") == "tradingview"]
    return {
        "provider": "TradingView",
        "universe": "IDX",
        "rows": len(parsed),
        "unique_tickers": len({r.get("ticker") for r in parsed}),
        "priced": sum(1 for r in parsed if r.get("value") is not None),
        "with_market_cap": sum(1 for r in parsed if r.get("market_cap_value")),
        "with_volume": sum(1 for r in parsed if r.get("volume")),
        "with_6m_performance": sum(1 for r in parsed if r.get("perf_6m") is not None),
        "industry_classified": sum(1 for r in parsed if r.get("industry")),
        "industry_missing": sum(1 for r in parsed if not r.get("industry")),
        "sector_by_exact_industry": sum(
            1 for r in parsed if r.get("sector_classification") == "industry_exact"),
        "sector_by_ticker_override": sum(
            1 for r in parsed if r.get("sector_classification") == "ticker_override"),
        "sector_by_provider_fallback": sum(
            1 for r in parsed if r.get("sector_classification") == "provider_sector_fallback"),
        "history_quality": "performance_checkpoints",
        "quote_mode": "near_realtime_snapshot",
        "licensed_realtime": False,
        "source_url": "https://scanner.tradingview.com/indonesia/scan",
    }
