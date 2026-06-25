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
    blob = f"{tv_sector or ''} {industry or ''}".lower()
    for sector, hints in INDUSTRY_HINTS:
        if any(h in blob for h in hints):
            return sector
    return TV_SECTOR_TO_COCKPIT.get(str(tv_sector or "").strip().lower(), "consumer")


def _jakarta_now() -> dt.datetime:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("Asia/Jakarta"))
    except Exception:  # noqa: BLE001
        return dt.datetime.now(dt.timezone(dt.timedelta(hours=7)))


def idx_session_state() -> dict:
    """Lightweight fallback state for price-only IDX scanner rows.

    Yahoo remains authoritative for scored/core rows. Scanner-only rows need a
    consistent state so they do not all render as stale closed assets during the
    Jakarta session.
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
    sector = _sector_key(data.get("sector"), data.get("industry"))
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
        "country_name": meta["name"],
        "country_flag": meta["flag"],
        "region": meta["region"],
        "market_cap_value": cap,
        "index_groups": ["idx_all"],
        "industry": data.get("industry") or "",
        "source_provider": "tradingview",
        "source_name": "TradingView",
        "source_url": TV_SYMBOL.format(ticker=ticker),
        "value": price,
        "delta_pct": dp,
        "volume": volume,
        "turnover": round((price or 0.0) * volume, 0),
    }


def idx_all_rows(rows: list[dict] | None = None) -> list[dict]:
    out = []
    for row in rows if rows is not None else scanner_rows():
        parsed = _parsed(row)
        if parsed:
            out.append(parsed)
    return out


def price_map(rows: list[dict] | None = None) -> dict[str, dict]:
    state = idx_session_state()
    prices = {}
    for row in idx_all_rows(rows):
        if row.get("value") is None:
            continue
        prices[row["source_symbol"]] = {
            "value": round(float(row["value"]), 4),
            "delta_pct": round(float(row.get("delta_pct") or 0.0), 2),
            "volume": float(row.get("volume") or 0.0),
            "turnover": float(row.get("turnover") or 0.0),
            "market_cap_value": row.get("market_cap_value"),
            "open": state["open"],
            "mkt_start": state["mkt_start"],
            "mkt_end": state["mkt_end"],
            "spark": [],
            "spark_ts": [],
            "intraday": [],
            "source": "tradingview_scanner",
        }
    return prices
