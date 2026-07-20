"""Authoritative market quotes via Yahoo's v8 chart endpoint (keyless, no auth).

Returns, per symbol: current value, the OFFICIAL previous close, the daily % exactly
as Yahoo/Bloomberg display it, whether the market is currently open, and the daily
close series (for sparklines + timeframe returns). This replaces hand-computing the
delta from yfinance `history()`, whose daily series is gappy for some instruments
(e.g. ^N225) and mislabeled multi-day moves as a 1-day change (the 5.13% bug).
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import time
import urllib.parse
import urllib.request

CHART_HOSTS = (
    "https://query2.finance.yahoo.com/v8/finance/chart/",
    "https://query1.finance.yahoo.com/v8/finance/chart/",
)


def _chart(sym: str, rng: str, interval: str, attempts: int = 3, timeout: int = 20) -> dict | None:
    for attempt in range(attempts):
        host = CHART_HOSTS[attempt % len(CHART_HOSTS)]
        url = f"{host}{urllib.parse.quote(sym)}?range={rng}&interval={interval}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)["chart"]["result"][0]
        except Exception:  # noqa: BLE001
            time.sleep(1.0 * (attempt + 1))
    return None


def _closes(res: dict) -> list:
    try:
        return [round(float(c), 4)
                for c in (res["indicators"]["quote"][0].get("close") or []) if c is not None]
    except Exception:  # noqa: BLE001 — some symbols have no intraday/quote block
        return []


def _series(res: dict) -> dict:
    """Aligned close/timestamp arrays for daily risk stats."""
    try:
        ts = res.get("timestamp") or []
        closes = res["indicators"]["quote"][0].get("close") or []
        pairs = [(int(t), round(float(c), 4)) for t, c in zip(ts, closes) if c is not None]
        return {"spark_ts": [p[0] for p in pairs], "spark": [p[1] for p in pairs]}
    except Exception:  # noqa: BLE001
        return {"spark_ts": [], "spark": []}


def _one(sym: str) -> dict | None:
    # range=1d&interval=30m → the OFFICIAL prior close (chartPreviousClose, the exact
    # anchor Yahoo/Bloomberg use for "today's %"), the live session bounds (open/closed),
    # AND the intraday series for the 24h chart — all in one call. (chartPreviousClose
    # is range-dependent: only range=1d gives yesterday's close, not the window start.)
    day = _chart(sym, "1d", "30m")
    if not day:
        return None
    m = day["meta"]
    price, pc = m.get("regularMarketPrice"), m.get("chartPreviousClose")
    if price is None or not pc:
        return None
    reg = (m.get("currentTradingPeriod") or {}).get("regular") or {}
    start, end = reg.get("start"), reg.get("end")
    now = int(time.time())
    intraday = _closes(day)
    out = {"value": round(float(price), 4),
           "prev_close": round(float(pc), 4),
           "delta_pct": round((price - pc) / pc * 100, 2),
           "open": bool(start and end and start <= now <= end),
           "mkt_start": start, "mkt_end": end,
           "quote_asof": int(m.get("regularMarketTime") or now),
           "quote_mode": "provider_snapshot",
           "intraday": intraday, "spark": [], "volume": 0.0,
           "chart_quality": {
               "24h": "real_intraday" if len(intraday) > 1 else "unavailable",
               "1W": "unavailable",
               "1M": "unavailable",
               "3M": "unavailable",
               "6M": "unavailable",
           }}
    # range=6mo&interval=1d → daily series for the 1W/1M/3M/6M sparkline + window returns
    six = _chart(sym, "6mo", "1d")
    if six:
        ser = _series(six)
        out["spark"] = ser["spark"][-130:]
        out["spark_ts"] = ser["spark_ts"][-130:]
        if len(out["spark"]) > 1:
            out["chart_asof"] = int(time.time())
            out["chart_quality"].update({
                "1W": "historical_close",
                "1M": "historical_close",
                "3M": "historical_close",
                "6M": "historical_close",
            })
        try:
            vols = [v for v in (six["indicators"]["quote"][0].get("volume") or []) if v is not None]
            out["volume"] = float(vols[-1]) if vols else 0.0
        except Exception:  # noqa: BLE001
            pass
    return out


def fetch(symbols: list, workers: int = 8) -> dict:
    """{symbol: {value, prev_close, delta_pct, open, spark}} — failed symbols omitted."""
    out, uniq = {}, list(dict.fromkeys(symbols))
    try:
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for sym, r in zip(uniq, ex.map(_one, uniq)):
                if r:
                    out[sym] = r
    except Exception as e:  # noqa: BLE001
        print(f"[yquote] fetch pool failed: {e}")
    print(f"[yquote] {len(out)}/{len(uniq)} symbols resolved via Yahoo v8")
    return out


def _lite_from_day(day: dict | None) -> dict | None:
    if not day:
        return None
    m = day.get("meta") or {}
    price, pc = m.get("regularMarketPrice"), m.get("chartPreviousClose")
    if price is None or not pc:
        return None
    reg = (m.get("currentTradingPeriod") or {}).get("regular") or {}
    start, end = reg.get("start"), reg.get("end")
    now = int(time.time())
    volume = 0.0
    try:
        vols = [v for v in (day["indicators"]["quote"][0].get("volume") or []) if v is not None]
        volume = float(vols[-1]) if vols else 0.0
    except Exception:  # noqa: BLE001
        pass
    intraday = _closes(day)
    return {
        "value": round(float(price), 4),
        "prev_close": round(float(pc), 4),
        "delta_pct": round((price - pc) / pc * 100, 2),
        "open": bool(start and end and start <= now <= end),
        "mkt_start": start,
        "mkt_end": end,
        "quote_asof": int(m.get("regularMarketTime") or now),
        "quote_mode": "provider_snapshot",
        "intraday": intraday,
        "spark": [],
        "spark_ts": [],
        "chart_asof": int(time.time()),
        "volume": volume,
        "turnover": round(float(price) * volume, 0),
        "chart_quality": {
            "24h": "real_intraday" if len(intraday) > 1 else "unavailable",
            "1W": "unavailable",
            "1M": "unavailable",
            "3M": "unavailable",
            "6M": "unavailable",
        },
    }


def _one_lite(sym: str) -> dict | None:
    """One-call quote for broad rows: price, official day %, state, 24h chart."""
    return _lite_from_day(_chart(sym, "1d", "30m"))


def _one_intraday_fast(sym: str) -> dict | None:
    """Bounded single-attempt intraday fetch for large rotating universes."""
    return _lite_from_day(_chart(sym, "1d", "30m", attempts=1, timeout=8))


def _one_history_fast(sym: str) -> dict | None:
    """Six-month observed daily closes without changing the live quote source."""
    six = _chart(sym, "6mo", "1d", attempts=2, timeout=12)
    if not six:
        return None
    series = _series(six)
    if len(series["spark"]) < 2:
        return None
    return {
        "spark": series["spark"][-130:],
        "spark_ts": series["spark_ts"][-130:],
        "history_asof": int(time.time()),
        "price_history_quality": "yahoo_historical_close",
        "chart_quality": {
            "1W": "historical_close",
            "1M": "historical_close",
            "3M": "historical_close",
            "6M": "historical_close",
        },
    }


def fetch_lite(symbols: list, workers: int = 10) -> dict:
    """Fast price-only pass for broad heatmap rows.

    Yahoo's batch quote endpoint currently returns 401 without a crumb, so this
    uses the same proven chart source as ``fetch`` but skips the 6-month daily
    call. Broad rows therefore get reliable 24h price/return and market state,
    while market-cap sizing is available only when supplied elsewhere.
    """
    out, uniq = {}, [s for s in dict.fromkeys(symbols) if s]
    try:
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for sym, r in zip(uniq, ex.map(_one_lite, uniq)):
                if r:
                    out[sym] = r
    except Exception as e:  # noqa: BLE001
        print(f"[yquote] quote-lite pool failed: {e}")
    print(f"[yquote] {len(out)}/{len(uniq)} symbols resolved via Yahoo chart-lite")
    return out


def fetch_intraday(symbols: list, workers: int = 16) -> dict:
    """Fast rotating 24h coverage; failures retain the prior cached chart."""
    out, uniq = {}, [s for s in dict.fromkeys(symbols) if s]
    try:
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for sym, row in zip(uniq, ex.map(_one_intraday_fast, uniq)):
                if row and row.get("intraday"):
                    out[sym] = row
    except Exception as e:  # noqa: BLE001
        print(f"[yquote] intraday rotation pool failed: {e}")
    print(f"[yquote] {len(out)}/{len(uniq)} symbols resolved via Yahoo intraday rotation")
    return out


def fetch_history(symbols: list, workers: int = 20) -> dict:
    """Fetch observed closes only, leaving TradingView-owned quote fields intact."""
    out, uniq = {}, [s for s in dict.fromkeys(symbols) if s]
    try:
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            for sym, row in zip(uniq, ex.map(_one_history_fast, uniq)):
                if row:
                    out[sym] = row
    except Exception as e:  # noqa: BLE001
        print(f"[yquote] history pool failed: {e}")
    print(f"[yquote] {len(out)}/{len(uniq)} symbols resolved via Yahoo daily history")
    return out
