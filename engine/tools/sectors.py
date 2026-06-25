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

from tools import universe


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
                    "volume": r.get("volume", 0.0),
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


def _row_cap(row: dict) -> float:
    try:
        return float(row.get("market_cap_value") or 0)
    except Exception:  # noqa: BLE001
        return 0.0


def collect(previous_sectors: list | None = None, telemetry: list | None = None) -> list:
    sector_rows = universe.priced_rows_by_sector()
    prices = {}
    if getattr(settings, "IDX_ALL_PRICE_ACTIVE", False):
        try:
            from tools import idx_membership
            prices.update(idx_membership.price_map())
        except Exception as e:  # noqa: BLE001
            print(f"[sectors] full IDX scanner overlay failed: {e}")

    if getattr(settings, "CRYPTO_TOP_PRICE_ACTIVE", False):
        try:
            from tools import crypto_quotes
            markets = crypto_quotes.top_markets(getattr(settings, "CRYPTO_TOP_PRICE_LIMIT", 100))
            universe._extend_by_sector(sector_rows, universe.crypto_top_rows(markets))
            prices.update(crypto_quotes.price_map_from_markets(markets))
            print(f"[sectors] CoinGecko top crypto rows: {len(markets)} markets")
        except Exception as e:  # noqa: BLE001
            print(f"[sectors] CoinGecko top crypto expansion failed: {e}")

    all_rows = [row for rows in sector_rows.values() for row in rows]
    rich_rows = [r for r in all_rows if r.get("data_tier") == universe.DATA_TIER_ACTIVE]
    price_only = [r for r in all_rows
                  if r.get("data_tier") != universe.DATA_TIER_ACTIVE
                  and not str(r.get("source_symbol", "")).startswith("CG:")]
    chart_limit = max(0, int(getattr(settings, "PRICE_ONLY_CHART_LIMIT", 160)))
    try:
        from tools import index_membership
        us_snapshot = index_membership.us_market_snapshot()
        for row in price_only:
            if row.get("country") != "US" or not row.get("index_groups"):
                continue
            snap = us_snapshot.get(row["ticker"])
            if snap and snap.get("value") is not None:
                prices[row["source_symbol"]] = snap
    except Exception as e:  # noqa: BLE001
        print(f"[sectors] US index snapshot overlay failed: {e}")

    chart_candidates = sorted(
        [r for r in price_only if not (prices.get(r["source_symbol"]) or {}).get("intraday")],
        key=_row_cap,
        reverse=True,
    )
    chart_rows = chart_candidates[:chart_limit]
    chart_symbols = {r["source_symbol"] for r in chart_rows}
    lite_rows = [r for r in price_only
                 if r["source_symbol"] not in prices and r["source_symbol"] not in chart_symbols]

    prices.update(_batch_prices([row["source_symbol"] for row in rich_rows]))
    if chart_rows or lite_rows:
        from tools import yquote
        prices.update(yquote.fetch_lite([row["source_symbol"] for row in chart_rows + lite_rows]))
    crypto_symbols = [row["source_symbol"] for rows in sector_rows.values() for row in rows
                      if row["country"] == "CR" and row["source_symbol"] in universe.CRYPTO_IDS]
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
        for base in sector_rows.get(sec["key"], []):
            ticker = base["ticker"]
            ysym = base["source_symbol"]
            country = base["country"]
            p = prices.get(ysym)
            delta = p["delta_pct"] if p else 0.0
            spark = p["spark"] if p else []
            rows.append(base | {
                "delta_pct": delta, "spark": spark,
                "spark_ts": (p or {}).get("spark_ts", []),
                "value": (p or {}).get("value", 0.0),
                "turnover": (p or {}).get("turnover", 0.0),
                "volume": (p or {}).get("volume", 0.0),
                "market_cap_value": (p or {}).get("market_cap_value") or base.get("market_cap_value"),
                "volume_24h": (p or {}).get("volume_24h"),
                "state": "open" if (p or {}).get("open") else "closed",
                "mkt_start": (p or {}).get("mkt_start"),
                "mkt_end": (p or {}).get("mkt_end"),
                "intraday": (p or {}).get("intraday", []),
            })
            if country == "ID":
                id_d.append(delta)
            elif country == "US":
                us_d.append(delta)

        try:
            from tools import fundamentals
            risk_benchmarks = fundamentals.risk_benchmarks_from_telemetry(telemetry)
            fundamentals.enrich(universe.scored_rows(rows), _previous_rows(previous_sectors),
                                refresh_hours=getattr(settings, "FUNDAMENTAL_REFRESH_HOURS", 24),
                                workers=getattr(settings, "FUNDAMENTAL_WORKERS", 6),
                                risk_benchmarks=risk_benchmarks)
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
    final_rows = [r for s in out for r in s["constituents"]]
    live = sum(1 for r in final_rows if r.get("spark") or r.get("intraday") or r.get("value"))
    print(f"[sectors] {len(out)} sectors, {live}/{len(final_rows)} constituents resolved")
    return out
