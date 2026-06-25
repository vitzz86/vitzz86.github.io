"""CoinGecko quote helpers for crypto rows.

Used only for crypto assets so dashboard BTC / sector crypto numbers share the
same 24h source. Chart calls are intentionally opt-in to avoid noisy API usage.
"""
from __future__ import annotations

import json
import time
import urllib.request

API = "https://api.coingecko.com/api/v3"
IDS = {"BTC-USD": "bitcoin", "ETH-USD": "ethereum", "SOL-USD": "solana",
       "BNB-USD": "binancecoin", "XRP-USD": "ripple", "ADA-USD": "cardano",
       "DOGE-USD": "dogecoin", "AVAX-USD": "avalanche-2", "LINK-USD": "chainlink",
       "MATIC-USD": "polygon-ecosystem-token"}
ALIASES = {"MATIC-USD": ["polygon-ecosystem-token", "matic-network"]}


def _get(url: str) -> dict:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            time.sleep(1.0 * (attempt + 1))
    return {}


def _ids_for(sym: str) -> list[str]:
    return ALIASES.get(sym) or ([IDS[sym]] if sym in IDS else [])


def simple(symbols: list[str]) -> dict:
    """{symbol: {value, delta_pct, prev_close, open}} from CoinGecko 24h fields."""
    ordered_ids = []
    for sym in symbols:
        ordered_ids.extend(_ids_for(sym))
    ids = ",".join(dict.fromkeys(ordered_ids))
    if not ids:
        return {}
    data = _get(f"{API}/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
                "&include_market_cap=true&include_24hr_vol=true")
    out = {}
    for sym in symbols:
        for cid in _ids_for(sym):
            row = data.get(cid) or {}
            price, dp = row.get("usd"), row.get("usd_24h_change")
            if price is None or dp is None:
                continue
            prev = price / (1 + dp / 100) if dp != -100 else price
            out[sym] = {"value": round(float(price), 4),
                        "delta_pct": round(float(dp), 2),
                        "prev_close": round(float(prev), 4),
                        "open": True, "mkt_start": None, "mkt_end": None,
                        "market_cap_value": row.get("usd_market_cap"),
                        "volume_24h": row.get("usd_24h_vol")}
            break
    return out


def chart(sym: str, days: int, interval: str = "") -> list:
    """CoinGecko price series for one symbol; tries aliases such as MATIC."""
    suffix = f"&interval={interval}" if interval else ""
    for cid in _ids_for(sym):
        data = _get(f"{API}/coins/{cid}/market_chart?vs_currency=usd&days={days}{suffix}")
        prices = [round(float(p[1]), 4) for p in (data.get("prices") or []) if len(p) > 1]
        if prices:
            return prices
    return []


def chart_series(sym: str, days: int, interval: str = "") -> dict:
    """CoinGecko price series with second timestamps for risk stats."""
    suffix = f"&interval={interval}" if interval else ""
    for cid in _ids_for(sym):
        data = _get(f"{API}/coins/{cid}/market_chart?vs_currency=usd&days={days}{suffix}")
        pairs = [(int(p[0] / 1000), round(float(p[1]), 4))
                 for p in (data.get("prices") or []) if len(p) > 1]
        if pairs:
            return {"spark_ts": [p[0] for p in pairs], "spark": [p[1] for p in pairs]}
    return {"spark_ts": [], "spark": []}


def top_markets(limit: int = 100) -> list[dict]:
    """Top crypto assets by market cap from CoinGecko markets.

    Used for price-only crypto heatmap coverage. Existing core crypto rows still
    use the explicit IDS map above so BTC/ETH/etc stay consistent everywhere.
    """
    per_page = max(1, min(int(limit or 100), 250))
    data = _get(
        f"{API}/coins/markets?vs_currency=usd&order=market_cap_desc"
        f"&per_page={per_page}&page=1&sparkline=false&price_change_percentage=24h"
    )
    return data if isinstance(data, list) else []


def price_map_from_markets(markets: list[dict]) -> dict:
    out = {}
    for row in markets or []:
        cid = row.get("id")
        price = row.get("current_price")
        dp = row.get("price_change_percentage_24h")
        if not cid or price is None:
            continue
        prev = price / (1 + (dp or 0.0) / 100) if dp != -100 else price
        out[f"CG:{cid}"] = {
            "value": round(float(price), 6),
            "delta_pct": round(float(dp or 0.0), 2),
            "prev_close": round(float(prev), 6),
            "open": True,
            "mkt_start": None,
            "mkt_end": None,
            "market_cap_value": row.get("market_cap"),
            "volume_24h": row.get("total_volume"),
            "volume": row.get("total_volume") or 0.0,
            "turnover": row.get("total_volume") or 0.0,
            "spark": [],
            "spark_ts": [],
            "intraday": [],
        }
    return out
