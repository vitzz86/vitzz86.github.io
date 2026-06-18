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
CG_SLUGS = {"MATIC-USD": "polygon"}


def _signal(agg: float) -> str:
    a = abs(agg)
    if a >= settings.SECTOR_SIGNAL_PCT["alert"]:
        return "ALERT"
    if a >= settings.SECTOR_SIGNAL_PCT["watch"]:
        return "WATCH"
    return "NORMAL"


def _batch_prices(symbols: list) -> dict:
    """Authoritative Yahoo v8 quotes for the universe → {symbol: {delta_pct, value,
    turnover, spark, open}}. Matches Yahoo/Bloomberg (official prior close, no gappy
    history mislabeling multi-day moves as 1-day)."""
    from tools import yquote
    out = {}
    for sym, r in yquote.fetch(symbols).items():
        out[sym] = {"delta_pct": r["delta_pct"], "value": round(r["value"], 2),
                    "turnover": round(r["value"] * r.get("volume", 0.0), 0),
                    "spark": r["spark"], "open": r["open"],
                    "spark_ts": r.get("spark_ts", []),
                    "intraday": r.get("intraday", []),
                    "mkt_start": r.get("mkt_start"), "mkt_end": r.get("mkt_end")}
    return out


def _previous_rows(previous_sectors: list | None) -> dict:
    rows = {}
    for sec in previous_sectors or []:
        for r in sec.get("constituents", []) or []:
            if r.get("source_symbol"):
                rows[r["source_symbol"]] = r
            if r.get("ticker"):
                rows[r["ticker"]] = r
    return rows


def collect(previous_sectors: list | None = None) -> list:
    symbols = [c[2] for sec in settings.SECTORS for c in sec["constituents"]]
    prices = _batch_prices(symbols)
    crypto_symbols = [c[2] for sec in settings.SECTORS for c in sec["constituents"]
                      if c[4] == "CR" and c[2] in CG_IDS]
    if crypto_symbols:
        try:
            from tools import crypto_quotes
            for sym, row in crypto_quotes.simple(crypto_symbols).items():
                prices.setdefault(sym, {}).update(row)
            # Yahoo sometimes drops migrated tokens (notably MATIC); fill only missing charts.
            for sym in crypto_symbols:
                p = prices.setdefault(sym, {})
                if not p.get("intraday"):
                    p["intraday"] = crypto_quotes.chart(sym, 1)
                if not p.get("spark"):
                    ser = crypto_quotes.chart_series(sym, 180, "daily")
                    p["spark"] = ser["spark"][-130:]
                    p["spark_ts"] = ser["spark_ts"][-130:]
        except Exception as e:  # noqa: BLE001
            print(f"[sectors] CoinGecko crypto overlay failed: {e}")

    out = []
    for sec in settings.SECTORS:
        rows, id_d, us_d = [], [], []
        for c in sec["constituents"]:
            ticker, name, ysym, exch, country, mktcap, tier = c[:7]
            p = prices.get(ysym)
            delta = p["delta_pct"] if p else 0.0
            spark = p["spark"] if p else []
            url = (COINGECKO + CG_SLUGS.get(ysym, CG_IDS[ysym])) if (country == "CR" and ysym in CG_IDS) \
                else (YF_QUOTE + ysym)
            rows.append({
                "ticker": ticker, "name": name, "exchange": exch,
                "country": country, "mktcap": mktcap, "tier": tier,
                "source_symbol": ysym,
                "delta_pct": delta, "spark": spark,
                "spark_ts": (p or {}).get("spark_ts", []),
                "value": (p or {}).get("value", 0.0),
                "turnover": (p or {}).get("turnover", 0.0),
                "market_cap_value": (p or {}).get("market_cap_value"),
                "volume_24h": (p or {}).get("volume_24h"),
                "state": "open" if (p or {}).get("open") else "closed",
                "mkt_start": (p or {}).get("mkt_start"),
                "mkt_end": (p or {}).get("mkt_end"),
                "intraday": (p or {}).get("intraday", []),
                "url": url,
            })
            if country == "ID":
                id_d.append(delta)
            elif country == "US":
                us_d.append(delta)

        try:
            from tools import fundamentals
            fundamentals.enrich(rows, _previous_rows(previous_sectors),
                                refresh_hours=getattr(settings, "FUNDAMENTAL_REFRESH_HOURS", 24),
                                workers=getattr(settings, "FUNDAMENTAL_WORKERS", 6))
        except Exception as e:  # noqa: BLE001
            print(f"[sectors] fundamental scoring failed: {e}")

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
