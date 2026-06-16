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
        out["spark"] = _closes(six)[-130:]
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
