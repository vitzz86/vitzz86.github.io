"""Sector Flow Matrix (PRD v2 · Module C) — baked at cron time for static hosting.

Batch-fetches the full 200-ticker universe via a single yfinance download, then
computes per-ticker day delta + sparkline, ID-vs-US sector aggregates, a
Mega/Large/Mid/Small tier badge, an ALERT/WATCH/NORMAL signal, and a synthesis
line. Every ticker carries a Yahoo Finance source URL (PRD: tickers link to
source). Degrades to flat 0.0 when offline so the grid always renders.
"""
from __future__ import annotations

import sys

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings

YF_QUOTE = "https://finance.yahoo.com/quote/"
COINGECKO = "https://www.coingecko.com/en/coins/"
CG_IDS = {"BTC-USD": "bitcoin", "ETH-USD": "ethereum", "SOL-USD": "solana",
          "BNB-USD": "binancecoin", "XRP-USD": "ripple", "ADA-USD": "cardano",
          "DOGE-USD": "dogecoin", "AVAX-USD": "avalanche-2", "LINK-USD": "chainlink",
          "MATIC-USD": "polygon-ecosystem-token"}


def _signal(agg: float) -> str:
    a = abs(agg)
    if a >= settings.SECTOR_SIGNAL_PCT["alert"]:
        return "ALERT"
    if a >= settings.SECTOR_SIGNAL_PCT["watch"]:
        return "WATCH"
    return "NORMAL"


def _batch_prices(symbols: list) -> dict:
    """One bulk download for the whole universe → {symbol: {delta_pct, spark}}."""
    out = {}
    try:
        import yfinance as yf
        # 1y of daily closes so 1D/1W/1M/YTD are genuinely distinct timeframes
        data = yf.download(symbols, period="1y", interval="1d",
                           group_by="ticker", threads=True, progress=False)
    except Exception as e:  # noqa: BLE001
        print(f"[sectors] batch download unavailable: {e}")
        return out
    for sym in symbols:
        try:
            col = data[sym]["Close"] if len(symbols) > 1 else data["Close"]
            closes = [float(c) for c in col.dropna().tolist()]
            if len(closes) < 2:
                continue
            value, prev = closes[-1], closes[-2]
            delta = (value - prev) / prev * 100 if prev else 0.0
            try:
                vcol = data[sym]["Volume"] if len(symbols) > 1 else data["Volume"]
                vol = float(vcol.dropna().tolist()[-1])
            except Exception:  # noqa: BLE001
                vol = 0.0
            # keep ~6mo of daily closes; client slices for 1W/1M/YTD timeframes
            out[sym] = {"delta_pct": round(delta, 2), "value": round(value, 2),
                        "turnover": round(value * vol, 0),
                        "spark": [round(c, 4) for c in closes[-130:]]}
        except Exception:  # noqa: BLE001 — one bad symbol never kills the batch
            continue
    return out


def collect() -> list:
    symbols = [c[2] for sec in settings.SECTORS for c in sec["constituents"]]
    prices = _batch_prices(symbols)

    out = []
    for sec in settings.SECTORS:
        rows, id_d, us_d = [], [], []
        for c in sec["constituents"]:
            ticker, name, ysym, exch, country, mktcap, tier = c[:7]
            p = prices.get(ysym)
            delta = p["delta_pct"] if p else 0.0
            spark = p["spark"] if p else []
            url = (COINGECKO + CG_IDS[ysym]) if (country == "CR" and ysym in CG_IDS) \
                else (YF_QUOTE + ysym)
            rows.append({
                "ticker": ticker, "name": name, "exchange": exch,
                "country": country, "mktcap": mktcap, "tier": tier,
                "delta_pct": delta, "spark": spark,
                "value": (p or {}).get("value", 0.0),
                "turnover": (p or {}).get("turnover", 0.0),
                "url": url,
            })
            if country == "ID":
                id_d.append(delta)
            elif country == "US":
                us_d.append(delta)

        all_d = [r["delta_pct"] for r in rows]
        id_agg = round(sum(id_d) / len(id_d), 2) if id_d else None
        us_agg = round(sum(us_d) / len(us_d), 2) if us_d else None
        # crypto / non-split sectors aggregate over all constituents
        agg = round(sum(all_d) / len(all_d), 2) if all_d else 0.0
        sl = [r["spark"] for r in rows if r["spark"]]
        sector_spark = []
        if sl:
            n = min(len(s) for s in sl)
            sl = [s[-n:] for s in sl]
            sector_spark = [round(sum(s[i] / s[0] for s in sl) / len(sl) * 100, 2)
                            for i in range(n)]

        ranked = sorted(rows, key=lambda r: r["delta_pct"], reverse=True)
        lead, lag = ranked[0], ranked[-1]
        if id_agg is not None and us_agg is not None:
            spread = "in step" if abs(id_agg - us_agg) < 0.4 else (
                "ID leading US" if id_agg > us_agg else "US leading ID")
            split = f" with {spread} ({id_agg:+.2f}% ID / {us_agg:+.2f}% US)"
        else:
            split = ""
        ai = (f"{sec['name']} is {'+' if agg >= 0 else ''}{agg:.2f}% on aggregate{split}. "
              f"{lead['ticker']} leads ({lead['delta_pct']:+.2f}%); "
              f"{lag['ticker']} lags ({lag['delta_pct']:+.2f}%). "
              + settings.SECTOR_THEMES.get(sec["key"], [""])[0] + ".")
        out.append({
            "key": sec["key"], "name": sec["name"], "icon": sec["icon"],
            "theme": sec["theme"], "change": agg, "idChange": id_agg,
            "usChange": us_agg, "signal": _signal(agg),
            "spark": sector_spark, "ai": ai,
            "volume": f"{len(rows)} tickers",
            "themes": settings.SECTOR_THEMES.get(sec["key"], []),
            "constituents": ranked,
        })
    live = sum(1 for s in out for r in s["constituents"] if r["spark"])
    print(f"[sectors] {len(out)} sectors, {live}/{len(symbols)} constituents with live data")
    return out
