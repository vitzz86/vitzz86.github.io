"""TradingView scanner overlay for non-US/global benchmark equities.

These rows exist for macro context, not full fundamental scoring. Yahoo gives
many of them usable current quotes but often misses historical daily candles.
TradingView scanner performance checkpoints give us a robust, low-cost 1W/1M/
3M/6M chart proxy, matching the IDX broad-universe approach.
"""
from __future__ import annotations

import json
import time
import urllib.request
from collections import defaultdict

from tools import idx_membership

TV_COLUMNS = [
    "name",
    "description",
    "close",
    "change",
    "volume",
    "market_cap_basic",
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
    "exchange",
]

MARKET_BY_COUNTRY = {
    "SG": "singapore",
    "JP": "japan",
    "KR": "korea",
    "TW": "taiwan",
    "HK": "hongkong",
    "AU": "australia",
    "IN": "india",
    "GB": "uk",
    "DE": "germany",
    "FR": "france",
    "CH": "switzerland",
    "NL": "netherlands",
    "ES": "spain",
    "DK": "denmark",
}

EXCHANGE_PREFIX = {
    "SGX": "SGX",
    "TSE": "TSE",
    "KRX": "KRX",
    "TWSE": "TWSE",
    "HKEX": "HKEX",
    "ASX": "ASX",
    "NSE": "NSE",
    "XETRA": "XETR",
    "SIX": "SIX",
    "LSE": "LSE",
    "BME": "BME",
    "EURONEXT": "EURONEXT",
    "EURONEXT PARIS": "EURONEXT",
    "NASDAQ COPENHAGEN": "OMXCOP",
}

SYMBOL_ALIASES = {
    "ROG.SW": "RO",
}


def _base_symbol(row: dict) -> str:
    raw = str(row.get("source_symbol") or row.get("ticker") or "").split(".", 1)[0]
    raw = SYMBOL_ALIASES.get(str(row.get("source_symbol") or ""), raw)
    raw = raw.replace("-", "_")
    if row.get("country") == "HK":
        raw = raw.lstrip("0") or raw
    return raw


def _tv_symbol(row: dict) -> tuple[str, str] | None:
    market = MARKET_BY_COUNTRY.get(row.get("country"))
    exchange = EXCHANGE_PREFIX.get(str(row.get("exchange") or "").upper())
    base = _base_symbol(row)
    if not market or not exchange or not base:
        return None
    return market, f"{exchange}:{base}"


def _scan(market: str, tickers: list[str]) -> list[dict]:
    payload = {
        "filter": [],
        "options": {"lang": "en"},
        "markets": [market],
        "symbols": {"query": {"types": []}, "tickers": tickers},
        "columns": TV_COLUMNS,
        "range": [0, len(tickers)],
    }
    req = urllib.request.Request(
        f"https://scanner.tradingview.com/{market}/scan",
        data=json.dumps(payload).encode(),
        headers={
            "User-Agent": "Mozilla/5.0 (Project Cockpit; global TV scanner)",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://www.tradingview.com",
            "Referer": "https://www.tradingview.com/",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=16) as res:  # noqa: S310
            return (json.load(res).get("data") or [])
    except Exception as exc:  # noqa: BLE001
        print(f"[tradingview_global] {market} scanner failed: {exc}")
        return []


def _parsed(vals: list) -> dict | None:
    if len(vals) < len(TV_COLUMNS):
        return None
    data = dict(zip(TV_COLUMNS, vals))
    close = idx_membership._num(data.get("close"))  # noqa: SLF001
    if close is None:
        return None
    spark = idx_membership._checkpoint_spark(close, data)  # noqa: SLF001
    cap = idx_membership._num(data.get("market_cap_basic"))  # noqa: SLF001
    volume = idx_membership._num(data.get("volume")) or 0.0  # noqa: SLF001
    return {
        "value": close,
        "delta_pct": idx_membership._num(data.get("change")) or 0.0,  # noqa: SLF001
        "market_cap_value": cap,
        "volume": volume,
        "turnover": idx_membership._num(data.get("Value.Traded")) or round(close * volume, 0),  # noqa: SLF001
        "avg_volume_10d": idx_membership._num(data.get("average_volume_10d_calc")),  # noqa: SLF001
        "avg_volume_30d": idx_membership._num(data.get("average_volume_30d_calc")),  # noqa: SLF001
        "relative_volume_10d": idx_membership._num(data.get("relative_volume_10d_calc")),  # noqa: SLF001
        "perf_1w": idx_membership._num(data.get("Perf.W")),  # noqa: SLF001
        "perf_1m": idx_membership._num(data.get("Perf.1M")),  # noqa: SLF001
        "perf_3m": idx_membership._num(data.get("Perf.3M")),  # noqa: SLF001
        "perf_6m": idx_membership._num(data.get("Perf.6M")),  # noqa: SLF001
        "perf_ytd": idx_membership._num(data.get("Perf.YTD")),  # noqa: SLF001
        "perf_1y": idx_membership._num(data.get("Perf.Y")),  # noqa: SLF001
        "volatility_1w": idx_membership._num(data.get("Volatility.W")),  # noqa: SLF001
        "volatility_1m": idx_membership._num(data.get("Volatility.M")),  # noqa: SLF001
        "volatility_1d": idx_membership._num(data.get("Volatility.D")),  # noqa: SLF001
        "recommend_all": idx_membership._num(data.get("Recommend.All")),  # noqa: SLF001
        "rsi": idx_membership._num(data.get("RSI")),  # noqa: SLF001
        "spark": spark,
        "spark_ts": idx_membership._checkpoint_ts(len(spark)) if spark else [],  # noqa: SLF001
        "chart_asof": int(time.time()),
        "price_history_quality": "tradingview_performance_checkpoints",
        "chart_quality": {
            "24h": "unavailable",
            "1W": "performance_checkpoint",
            "1M": "performance_checkpoint",
            "3M": "performance_checkpoint",
            "6M": "performance_checkpoint",
        },
    }


def price_map(rows: list[dict]) -> dict:
    grouped: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in rows:
        item = _tv_symbol(row)
        if item:
            market, tv = item
            grouped[market].append((row.get("source_symbol") or row.get("ticker"), tv))

    out = {}
    for market, items in grouped.items():
        result = _scan(market, [tv for _, tv in items])
        by_symbol = {r.get("s"): r for r in result}
        by_name = {}
        for r in result:
            vals = r.get("d") or []
            if vals:
                by_name[str(vals[0])] = r
        for source, tv in items:
            hit = by_symbol.get(tv) or by_name.get(tv.split(":", 1)[-1])
            parsed = _parsed(hit.get("d") or []) if hit else None
            if parsed:
                out[source] = parsed
    total = sum(len(v) for v in grouped.values())
    if total:
        print(f"[tradingview_global] {len(out)}/{total} global benchmark rows resolved")
    return out
