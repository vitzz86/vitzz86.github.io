"""Sector Flow Matrix (PRD v2 · Module C) — baked at cron time for static hosting.

Fetches each constituent's day delta + a short sparkline via yfinance, computes
ID-vs-US aggregates and an ALERT/WATCH/NORMAL signal per sector, and emits a
JSON-ready structure the static cockpit renders client-side. No live backend:
everything the dashboard needs is pre-compiled here.

Every public helper degrades gracefully — a dead ticker or an offline yfinance
never raises past collect(); missing prices fall back to a flat 0.0 so the grid
always renders.
"""
from __future__ import annotations

import sys

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings


def _signal(agg: float) -> str:
    a = abs(agg)
    if a >= settings.SECTOR_SIGNAL_PCT["alert"]:
        return "ALERT"
    if a >= settings.SECTOR_SIGNAL_PCT["watch"]:
        return "WATCH"
    return "NORMAL"


def _fetch_one(yf, symbol: str) -> dict | None:
    """Returns {delta_pct, spark:[...], value} or None on failure."""
    try:
        hist = yf.Ticker(symbol).history(period="1mo", interval="1d")
        closes = hist["Close"].dropna().tolist()
        if len(closes) < 2:
            return None
        value, prev = float(closes[-1]), float(closes[-2])
        delta = (value - prev) / prev * 100 if prev else 0.0
        spark = [round(float(c), 4) for c in closes[-20:]]
        return {"delta_pct": round(delta, 2), "spark": spark, "value": round(value, 2)}
    except Exception as e:  # noqa: BLE001
        print(f"[sectors] {symbol} failed: {e}")
        return None


def collect() -> list:
    """Returns the sectors payload list. Live yfinance where reachable, else a
    deterministic fallback so the matrix always has content."""
    try:
        import yfinance as yf
    except Exception:  # noqa: BLE001
        yf = None

    out = []
    for sec in settings.SECTORS:
        rows, id_d, us_d = [], [], []
        for c in sec["constituents"]:
            ticker, name, ysym, exch, country, mktcap, tier = c[:7]
            spec = "spec" in c[7:]
            data = _fetch_one(yf, ysym) if yf else None
            delta = data["delta_pct"] if data else 0.0
            spark = data["spark"] if data else []
            rows.append({
                "ticker": ticker, "name": name, "exchange": exch,
                "country": country, "mktcap": mktcap, "tier": tier,
                "delta_pct": delta, "spark": spark, "speculative": spec,
            })
            (id_d if country == "ID" else us_d).append(delta)

        id_agg = round(sum(id_d) / len(id_d), 2) if id_d else 0.0
        us_agg = round(sum(us_d) / len(us_d), 2) if us_d else 0.0
        agg = round((id_agg + us_agg) / 2, 2)
        # sector sparkline = mean of constituent sparklines (normalized length)
        sl = [r["spark"] for r in rows if r["spark"]]
        sector_spark = []
        if sl:
            n = min(len(s) for s in sl)
            sl = [s[-n:] for s in sl]
            sector_spark = [round(sum(s[i] / s[0] for s in sl) / len(sl) * 100, 2)
                            for i in range(n)]
        ranked = sorted(rows, key=lambda r: r["delta_pct"], reverse=True)
        lead, lag = ranked[0], ranked[-1]
        spread = "in step" if abs(id_agg - us_agg) < 0.4 else (
            "ID leading US" if id_agg > us_agg else "US leading ID")
        ai = (f"{sec['name']} is {'+' if agg >= 0 else ''}{agg:.2f}% on aggregate "
              f"with {spread} ({id_agg:+.2f}% ID / {us_agg:+.2f}% US). "
              f"{lead['ticker']} leads ({lead['delta_pct']:+.2f}%); "
              f"{lag['ticker']} lags ({lag['delta_pct']:+.2f}%). "
              + settings.SECTOR_THEMES.get(sec["key"], [""])[0] + ".")
        out.append({
            "key": sec["key"], "name": sec["name"], "icon": sec["icon"],
            "theme": sec["theme"], "change": agg, "idChange": id_agg,
            "usChange": us_agg, "signal": _signal(agg),
            "spark": sector_spark, "ai": ai,
            "themes": settings.SECTOR_THEMES.get(sec["key"], []),
            "constituents": ranked,
        })
    live = sum(1 for s in out for r in s["constituents"] if r["spark"])
    print(f"[sectors] {len(out)} sectors, {live} constituents with live data")
    return out
