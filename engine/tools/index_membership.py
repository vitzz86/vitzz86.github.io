"""Dynamic price-only index membership for broad market heatmaps.

The scored Sector Flow universe stays curated. These helpers add broad US
membership views as quote-only rows so S&P 500 and Nasdaq 100 can be monitored
without running fundamentals and DeepSeek over every constituent.
"""
from __future__ import annotations

import sys
import json
import urllib.request
from functools import lru_cache
from html import unescape
from html.parser import HTMLParser

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"
NASDAQ_SCREENER = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=9000&offset=0&download=true"
NASDAQ100_API = "https://api.nasdaq.com/api/quote/list-type/nasdaq100"

# Last-known official membership keeps the dashboard populated during a brief
# Nasdaq API outage. The official endpoint remains authoritative every run.
NASDAQ100_FALLBACK = (
    "AAPL", "AMAT", "AMGN", "CMCSA", "INTC", "KLAC", "PCAR", "CTAS", "PAYX", "LRCX",
    "ADSK", "ROST", "MNST", "MSFT", "ADBE", "FAST", "EA", "CSCO", "REGN", "IDXX",
    "VRTX", "ODFL", "QCOM", "GILD", "SNPS", "SBUX", "INTU", "MCHP", "ORLY", "COST",
    "CPRT", "ASML", "TTWO", "AMZN", "MSTR", "NVDA", "BKNG", "ISRG", "MRVL", "ADI",
    "AEP", "AMD", "ADP", "CDNS", "CSX", "HON", "MAR", "MU", "XEL", "EXC", "PEP",
    "ROP", "TER", "TXN", "WDC", "WMT", "AXON", "MDLZ", "NFLX", "STX", "ALNY",
    "GOOGL", "MPWR", "DXCM", "TMUS", "MELI", "KDP", "NBIS", "AVGO", "FTNT", "TSLA",
    "NXPI", "FANG", "META", "PANW", "WDAY", "GOOG", "PYPL", "SHOP", "KHC", "LITE",
    "CCEP", "BKR", "PDD", "CRWD", "DDOG", "RKLB", "PLTR", "ABNB", "DASH", "APP",
    "CEG", "WBD", "GEHC", "LIN", "ARM", "TRI", "FER", "ALAB", "SNDK", "CRWV",
    "SPCX", "HONA",
)

GICS_TO_SECTOR = {
    "basic materials": "energy",
    "communication services": "entertainment",
    "consumer services": "consumer",
    "consumer discretionary": "consumer",
    "consumer staples": "consumer",
    "energy": "energy",
    "financials": "financials",
    "health care": "healthcare",
    "healthcare": "healthcare",
    "industrials": "infrastructure",
    "information technology": "technology",
    "materials": "energy",
    "real estate": "property",
    "technology": "technology",
    "telecommunications": "technology",
    "utilities": "renewables",
}


class _WikiTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._capture = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
            self._capture = True

    def handle_data(self, data):
        if self._capture and self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            txt = " ".join("".join(self._cell).split())
            self._row.append(unescape(txt))
            self._cell = None
            self._capture = False
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def _tables(url: str) -> list[list[dict]]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", "ignore")
        parser = _WikiTableParser()
        parser.feed(html)
        out = []
        for table in parser.tables:
            if not table:
                continue
            headers = [h.strip() for h in table[0]]
            if not headers:
                continue
            rows = []
            for row in table[1:]:
                if len(row) < min(2, len(headers)):
                    continue
                if len(row) < len(headers):
                    row = row + [""] * (len(headers) - len(row))
                rows.append(dict(zip(headers, row[:len(headers)])))
            if rows:
                out.append(rows)
        return out
    except Exception as e:  # noqa: BLE001
        print(f"[index_membership] failed to read {url}: {e}")
        return []


def _sector_key(raw: str | None) -> str:
    key = str(raw or "").strip().lower()
    return GICS_TO_SECTOR.get(key, "technology")


def _yf_symbol(sym: str) -> str:
    # Yahoo uses BRK-B / BF-B while index tables usually use BRK.B / BF.B.
    return str(sym or "").strip().replace(".", "-")


def _norm_symbol(sym: str) -> str:
    return _yf_symbol(sym).replace("/", "-").upper()


def _fmt_cap(value: float | int | None) -> str:
    try:
        n = float(value or 0)
    except Exception:  # noqa: BLE001
        n = 0
    if n >= 1e12:
        return f"${n / 1e12:.1f}T"
    if n >= 1e9:
        return f"${n / 1e9:.0f}B"
    if n >= 1e6:
        return f"${n / 1e6:.0f}M"
    return ""


def _tier_from_cap(value: float | int | None) -> str:
    try:
        n = float(value or 0)
    except Exception:  # noqa: BLE001
        n = 0
    if n >= 250_000_000_000:
        return "mega"
    if n >= 50_000_000_000:
        return "large"
    if n >= 5_000_000_000:
        return "mid"
    return "small"


def _num(raw) -> float | None:
    if raw is None:
        return None
    txt = str(raw).replace("$", "").replace("%", "").replace(",", "").strip()
    if not txt or txt in ("--", "N/A"):
        return None
    try:
        return float(txt)
    except Exception:  # noqa: BLE001
        return None


@lru_cache(maxsize=1)
def us_market_snapshot() -> dict[str, dict]:
    try:
        req = urllib.request.Request(
            NASDAQ_SCREENER,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Origin": "https://www.nasdaq.com",
                "Referer": "https://www.nasdaq.com/market-activity/stocks/screener",
            },
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            rows = json.load(r).get("data", {}).get("rows", [])
        out = {}
        for row in rows:
            sym = _norm_symbol(row.get("symbol", ""))
            price = _num(row.get("lastsale"))
            dp = _num(row.get("pctchange"))
            volume = _num(row.get("volume")) or 0.0
            cap = _num(row.get("marketCap"))
            if not sym:
                continue
            out[sym] = {
                "value": round(price, 4) if price is not None else None,
                "delta_pct": round(dp, 2) if dp is not None else 0.0,
                "open": False,
                "mkt_start": None,
                "mkt_end": None,
                "market_cap_value": cap,
                "volume": volume,
                "turnover": round((price or 0.0) * volume, 0),
                "name": str(row.get("name") or sym).strip(),
                "sector": str(row.get("sector") or "").strip(),
                "industry": str(row.get("industry") or "").strip(),
                "spark": [],
                "spark_ts": [],
                "intraday": [],
                "source": "nasdaq_screener",
            }
        print(f"[index_membership] US market snapshot: {len(out)} rows")
        return out
    except Exception as e:  # noqa: BLE001
        print(f"[index_membership] US market snapshot failed: {e}")
        return {}


def us_market_caps() -> dict[str, float]:
    snap = us_market_snapshot()
    return {sym: row["market_cap_value"] for sym, row in snap.items()
            if row.get("market_cap_value")}


def _row(symbol: str, name: str, gics: str, group: str) -> dict:
    sym = _yf_symbol(symbol)
    sector = _sector_key(gics)
    return {
        "ticker": sym,
        "name": str(name or sym).strip(),
        "source_symbol": sym,
        "exchange": "US",
        "country": "US",
        "mktcap": "",
        "tier": "large",
        "market_cap_value": None,
        "sector_key": sector,
        "sector_name": sector,
        "country_name": settings.COUNTRY_META["US"]["name"],
        "country_flag": settings.COUNTRY_META["US"]["flag"],
        "region": settings.COUNTRY_META["US"]["region"],
        "universe": ["US_INDEX_MEMBERSHIP", group],
        "index_groups": [group],
        "data_tier": "price_only",
        "active": True,
        "price_frequency": "30m_quote_lite",
        "fundamental_frequency_hours": None,
        "news_priority": "watch",
        "url": settings.YF_QUOTE + sym,
    }


def sp500_rows(limit: int | None = None) -> list[dict]:
    rows = []
    for table in _tables(SP500_URL):
        cols = {str(c).lower(): c for c in table[0].keys()}
        if "symbol" not in cols or "security" not in cols:
            continue
        sector_col = cols.get("gics sector") or cols.get("sector")
        for r in table:
            rows.append(_row(r.get(cols["symbol"]), r.get(cols["security"]),
                             r.get(sector_col, "") if sector_col else "", "sp500"))
        break
    if limit:
        rows = rows[:limit]
    print(f"[index_membership] S&P 500 rows: {len(rows)}")
    return rows


@lru_cache(maxsize=1)
def _official_nasdaq100() -> tuple[dict, ...]:
    try:
        req = urllib.request.Request(
            NASDAQ100_API,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Origin": "https://www.nasdaq.com",
                "Referer": "https://www.nasdaq.com/market-activity/quotes/nasdaq-ndx-index",
            },
        )
        with urllib.request.urlopen(req, timeout=25) as response:
            payload = json.load(response)
        rows = payload.get("data", {}).get("data", {}).get("rows", [])
        clean = tuple(row for row in rows if _norm_symbol(row.get("symbol")))
        if len(clean) >= 90:
            return clean
        print(f"[index_membership] official Nasdaq 100 response incomplete: {len(clean)} rows")
    except Exception as e:  # noqa: BLE001
        print(f"[index_membership] official Nasdaq 100 failed: {e}")
    return ()


def nasdaq100_rows(limit: int | None = None, market_snapshot: dict | None = None) -> list[dict]:
    market_snapshot = market_snapshot or {}
    official = _official_nasdaq100()
    members = official or tuple({"symbol": sym, "companyName": sym} for sym in NASDAQ100_FALLBACK)
    rows = []
    for item in members:
        sym = _norm_symbol(item.get("symbol"))
        market = market_snapshot.get(sym, {})
        name = item.get("companyName") or market.get("name") or sym
        sector = market.get("sector") or "Information Technology"
        row = _row(sym, name, sector, "nasdaq100")
        cap = _num(item.get("marketCap")) or market.get("market_cap_value")
        if cap:
            row["market_cap_value"] = cap
            row["mktcap"] = _fmt_cap(cap)
            row["tier"] = _tier_from_cap(cap)
        if market.get("industry"):
            row["industry"] = market["industry"]
        row["source_provider"] = "nasdaq"
        row["source_name"] = "Nasdaq-100"
        row["source_url"] = "https://www.nasdaq.com/NDX"
        rows.append(row)
    if limit:
        rows = rows[:limit]
    source = "official" if official else "fallback"
    print(f"[index_membership] Nasdaq 100 rows: {len(rows)} ({source})")
    return rows


def us_index_rows() -> list[dict]:
    limits = getattr(settings, "US_INDEX_LIMITS", {})
    market_snapshot = us_market_snapshot()
    rows = []
    if getattr(settings, "SP500_PRICE_ACTIVE", True):
        rows.extend(sp500_rows(limits.get("sp500")))
    if getattr(settings, "NASDAQ100_PRICE_ACTIVE", True):
        rows.extend(nasdaq100_rows(limits.get("nasdaq100"), market_snapshot))
    caps = {sym: row["market_cap_value"] for sym, row in market_snapshot.items()
            if row.get("market_cap_value")} if rows else {}
    for row in rows:
        cap = caps.get(_norm_symbol(row.get("ticker")))
        if cap:
            row["market_cap_value"] = cap
            row["mktcap"] = _fmt_cap(cap)
            row["tier"] = _tier_from_cap(cap)
    return rows
