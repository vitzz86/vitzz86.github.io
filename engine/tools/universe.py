"""Universe registry helpers for Project Cockpit.

This module is intentionally data-shaping only. It normalizes the currently
active Sector Flow universe and the mapped-but-not-active global leaders so the
dashboard can scale without each surface inventing its own country, region,
source, and refresh-tier rules.
"""
from __future__ import annotations

import sys

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings

YF_QUOTE = "https://finance.yahoo.com/quote/"
COINGECKO = "https://www.coingecko.com/en/coins/"
CRYPTO_IDS = {"BTC-USD": "bitcoin", "ETH-USD": "ethereum", "SOL-USD": "solana",
              "BNB-USD": "binancecoin", "XRP-USD": "ripple", "ADA-USD": "cardano",
              "DOGE-USD": "dogecoin", "AVAX-USD": "avalanche-2", "LINK-USD": "chainlink",
              "MATIC-USD": "polygon-ecosystem-token"}
CRYPTO_SLUGS = {"MATIC-USD": "polygon"}

ACTIVE_UNIVERSE = "SECTOR_FLOW"
GLOBAL_LEADERS_UNIVERSE = "GLOBAL_LEADERS_V1"

DATA_TIER_ACTIVE = "scored"
DATA_TIER_PRICE_ONLY = "price_only"
DATA_TIER_MAPPED = "mapped_not_active"

NEXT_TARGETS = [
    {"key": "full_idx", "label": "All IDX tickers", "status": "planned"},
    {"key": "sp500", "label": "S&P 500 constituents", "status": "planned"},
    {"key": "nasdaq100", "label": "Nasdaq 100 constituents", "status": "planned"},
    {"key": "crypto_top100", "label": "Top 100 crypto by market cap", "status": "planned"},
]


def country_meta(country: str) -> dict:
    meta = getattr(settings, "COUNTRY_META", {}).get(country, {})
    return {
        "country_name": meta.get("name", country),
        "country_flag": meta.get("flag", ""),
        "region": meta.get("region", country),
    }


def source_url(row: dict) -> str:
    symbol = row.get("source_symbol") or ""
    if row.get("country") == "CR" and symbol in CRYPTO_IDS:
        return COINGECKO + CRYPTO_SLUGS.get(symbol, CRYPTO_IDS[symbol])
    return YF_QUOTE + symbol


def _row_key(row: dict) -> str:
    return f"{row.get('country', '')}|{row.get('ticker', '')}|{row.get('source_symbol', '')}"


def _active_row(sector: dict, item: tuple) -> dict:
    ticker, name, symbol, exchange, country, mktcap, tier = item[:7]
    meta = country_meta(country)
    row = {
        "ticker": ticker,
        "name": name,
        "source_symbol": symbol,
        "exchange": exchange,
        "country": country,
        "mktcap": mktcap,
        "tier": tier,
        "flags": list(item[7:]),
        "sector_key": sector["key"],
        "sector_name": sector["name"],
        "country_name": meta["country_name"],
        "country_flag": meta["country_flag"],
        "region": meta["region"],
        "universe": [ACTIVE_UNIVERSE],
        "data_tier": DATA_TIER_ACTIVE,
        "active": True,
        "price_frequency": "30m",
        "fundamental_frequency_hours": getattr(settings, "FUNDAMENTAL_REFRESH_HOURS", 24),
        "news_priority": "priority",
    }
    row["url"] = source_url(row)
    return row


def active_rows_by_sector() -> dict[str, list[dict]]:
    return {
        sec["key"]: [_active_row(sec, item) for item in sec.get("constituents", [])]
        for sec in settings.SECTORS
    }


def active_rows() -> list[dict]:
    return [row for rows in active_rows_by_sector().values() for row in rows]


def active_symbols() -> list[str]:
    return [row["source_symbol"] for row in active_rows()]


def active_crypto_symbols() -> list[str]:
    return [row["source_symbol"] for row in active_rows()
            if row.get("country") == "CR" and row.get("source_symbol") in CRYPTO_IDS]


def global_leader_rows(price_active: bool | None = None) -> list[dict]:
    if price_active is None:
        price_active = bool(getattr(settings, "GLOBAL_LEADERS_PRICE_ACTIVE", False))
    rows = []
    for item in getattr(settings, "GLOBAL_LEADERS_V1", []):
        meta = country_meta(item.get("country", ""))
        active = bool(price_active)
        row = {
            "ticker": item.get("ticker", ""),
            "name": item.get("name", ""),
            "source_symbol": item.get("source_symbol", ""),
            "exchange": item.get("exchange", ""),
            "country": item.get("country", ""),
            "mktcap": item.get("mktcap", ""),
            "tier": item.get("tier", ""),
            "sector_key": item.get("sector", ""),
            "sector_name": item.get("sector", ""),
            "country_name": meta["country_name"],
            "country_flag": meta["country_flag"],
            "region": meta["region"],
            "universe": [GLOBAL_LEADERS_UNIVERSE],
            "data_tier": DATA_TIER_PRICE_ONLY if active else DATA_TIER_MAPPED,
            "active": active,
            "price_frequency": "30m" if active else "not_active",
            "fundamental_frequency_hours": None,
            "news_priority": "watch",
        }
        row["url"] = source_url(row)
        rows.append(row)
    return rows


def global_leaders_by_sector(price_active: bool | None = None) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for row in global_leader_rows(price_active=price_active):
        out.setdefault(row["sector_key"], []).append(row)
    return out


def priced_rows_by_sector() -> dict[str, list[dict]]:
    rows = active_rows_by_sector()
    if getattr(settings, "GLOBAL_LEADERS_PRICE_ACTIVE", False):
        for key, leaders in global_leaders_by_sector(price_active=True).items():
            rows.setdefault(key, []).extend(leaders)
    return rows


def priced_rows() -> list[dict]:
    return [row for rows in priced_rows_by_sector().values() for row in rows]


def priced_symbols() -> list[str]:
    return [row["source_symbol"] for row in priced_rows()]


def scored_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row.get("data_tier") == DATA_TIER_ACTIVE]


def counts(rows: list[dict], key: str) -> dict:
    out: dict[str, int] = {}
    for row in rows:
        val = row.get(key) or "UNKNOWN"
        out[val] = out.get(val, 0) + 1
    return dict(sorted(out.items()))


def dedupe(rows: list[dict]) -> list[dict]:
    out: dict[str, dict] = {}
    for row in rows:
        out.setdefault(_row_key(row), row)
    return list(out.values())


def coverage_summary(sectors_list: list | None = None) -> dict:
    if sectors_list is None:
        active = priced_rows()
    else:
        active = [c for s in sectors_list for c in s.get("constituents", [])]
    unique_active = dedupe(active)
    leaders = global_leader_rows(price_active=getattr(settings, "GLOBAL_LEADERS_PRICE_ACTIVE", False))
    active_tiers = counts(active, "data_tier")
    return {
        "active_sector_flow": {
            "count": len(active),
            "unique_assets": len(unique_active),
            "countries": counts(active, "country"),
            "regions": counts(active, "region"),
            "sectors": counts(active, "sector_key"),
            "data_tiers": active_tiers,
            "status": "active_priced_mixed_tiers" if active_tiers.get(DATA_TIER_PRICE_ONLY)
            else "active_priced_scored",
        },
        "global_leaders_v1": {
            "count": len(leaders),
            "countries": counts(leaders, "country"),
            "regions": counts(leaders, "region"),
            "sectors": counts(leaders, "sector_key"),
            "data_tiers": counts(leaders, "data_tier"),
            "status": DATA_TIER_PRICE_ONLY if getattr(settings, "GLOBAL_LEADERS_PRICE_ACTIVE", False)
            else DATA_TIER_MAPPED,
        },
        "registry": {
            "active_universes": [ACTIVE_UNIVERSE]
            + ([GLOBAL_LEADERS_UNIVERSE] if getattr(settings, "GLOBAL_LEADERS_PRICE_ACTIVE", False)
               else []),
            "mapped_universes": [] if getattr(settings, "GLOBAL_LEADERS_PRICE_ACTIVE", False)
            else [GLOBAL_LEADERS_UNIVERSE],
            "next_targets": NEXT_TARGETS,
        },
    }
