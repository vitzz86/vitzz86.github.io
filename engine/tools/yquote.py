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

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/"


def _chart(sym: str, rng: str, interval: str) -> dict | None:
    url = f"{CHART}{urllib.parse.quote(sym)}?range={rng}&interval={interval}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
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
    out = {"value": round(float(price), 4),
           "prev_close": round(float(pc), 4),
           "delta_pct": round((price - pc) / pc * 100, 2),
           "open": bool(start and end and start <= now <= end),
           "mkt_start": start, "mkt_end": end,
           "intraday": _closes(day), "spark": [], "volume": 0.0}
    # range=6mo&interval=1d → daily series for the 1W/1M/3M/6M sparkline + window returns
    six = _chart(sym, "6mo", "1d")
    if six:
        ser = _series(six)
        out["spark"] = ser["spark"][-130:]
        out["spark_ts"] = ser["spark_ts"][-130:]
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


def _one_lite(sym: str) -> dict | None:
    """One-call quote for broad rows: price, official day %, state, 24h chart."""
    day = _chart(sym, "1d", "30m")
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
    return {
        "value": round(float(price), 4),
        "prev_close": round(float(pc), 4),
        "delta_pct": round((price - pc) / pc * 100, 2),
        "open": bool(start and end and start <= now <= end),
        "mkt_start": start,
        "mkt_end": end,
        "intraday": _closes(day),
        "spark": [],
        "spark_ts": [],
        "volume": volume,
        "turnover": round(float(price) * volume, 0),
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
