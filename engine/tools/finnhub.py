"""Finnhub chart fallback for broad non-IDX equity rows.

Yahoo is still the primary keyless quote path for non-IDX equities, but it can
rate-limit chart history on larger universes. Finnhub is already configured for
live US quotes; this helper uses the same key to fill missing historical chart
data without changing IDX's TradingView source of truth.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

from config import settings

BASE = "https://finnhub.io/api/v1/stock/candle"


def _get(symbol: str, resolution: str, start: int, end: int) -> dict | None:
    key = settings.FINNHUB_API_KEY
    if not key:
        return None
    query = urllib.parse.urlencode({
        "symbol": symbol,
        "resolution": resolution,
        "from": start,
        "to": end,
        "token": key,
    })
    try:
        req = urllib.request.Request(f"{BASE}?{query}", headers={"User-Agent": "Project Cockpit"})
        with urllib.request.urlopen(req, timeout=12) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _symbol(sym: str) -> str:
    # Finnhub uses plain US tickers and generally accepts Yahoo-style suffixes
    # for many international listings (e.g. 0700.HK, ASML.AS).
    return (sym or "").replace("-", ".")


def chart_series(symbols: list[str], limit: int = 60, sleep_s: float = 1.05) -> dict:
    if not settings.FINNHUB_API_KEY:
        return {}
    out = {}
    now = int(time.time())
    start = now - 190 * 86400
    for raw in list(dict.fromkeys([s for s in symbols if s]))[:max(0, limit)]:
        sym = _symbol(raw)
        data = _get(sym, "D", start, now)
        if data and data.get("s") == "ok" and data.get("c") and data.get("t"):
            closes = [round(float(v), 4) for v in data["c"] if v is not None]
            stamps = [int(v) for v in data["t"] if v is not None]
            if closes:
                out[raw] = {
                    "spark": closes[-130:],
                    "spark_ts": stamps[-130:],
                    "chart_asof": now,
                    "price_history_quality": "finnhub_historical_close",
                    "chart_quality": {
                        "24h": "unavailable",
                        "1W": "historical_close",
                        "1M": "historical_close",
                        "3M": "historical_close",
                        "6M": "historical_close",
                    },
                }
        time.sleep(max(0.0, sleep_s))
    if symbols:
        print(f"[finnhub] {len(out)}/{min(len(set(symbols)), limit)} symbols resolved via candle fallback")
    return out
