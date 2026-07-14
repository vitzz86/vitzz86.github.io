"""Sector Flow Matrix (PRD v2 · Module C) — baked at cron time for static hosting.

Builds the active market universe from provider-specific feeds, computes
per-ticker day delta + sparkline, ID-vs-US sector aggregates, a Mega/Large/Mid/
Small tier badge, an ALERT/WATCH/NORMAL signal, and a synthesis line. IDX quote
coverage is TradingView-first; Yahoo remains the generic fallback/feed for
non-IDX equities and curated fundamentals.
"""
from __future__ import annotations

import time
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
                    "chart_quality": r.get("chart_quality"),
                    "chart_asof": r.get("chart_asof"),
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


def _uses_tradingview_idx(row: dict) -> bool:
    return row.get("country") == "ID" and row.get("source_provider") == "tradingview"


def _pick_price_field(price: dict, base: dict, key: str):
    return price.get(key) if price.get(key) is not None else base.get(key)


def _chart_cache_fresh(row: dict, max_age_hours: float) -> bool:
    asof = row.get("chart_asof")
    if not asof:
        return False
    try:
        return (time.time() - float(asof)) <= max_age_hours * 3600
    except Exception:  # noqa: BLE001
        return False


def _merge_cached_charts(prices: dict, rows: list[dict], previous_sectors: list | None) -> None:
    """Reuse broad price-only 6M charts so Yahoo backfill can converge safely."""
    prev = _previous_rows(previous_sectors)
    max_age = float(getattr(settings, "PRICE_ONLY_CHART_CACHE_HOURS", 36))
    for row in rows:
        sym = row.get("source_symbol")
        if not sym or sym not in prices:
            continue
        cached = prev.get(sym) or prev.get(row.get("ticker"))
        if not cached or not cached.get("spark"):
            continue
        p = prices.setdefault(sym, {})
        if not p.get("spark"):
            p["spark"] = cached.get("spark") or []
            p["spark_ts"] = cached.get("spark_ts") or []
            p["price_history_quality"] = cached.get("price_history_quality")
            p["chart_asof"] = cached.get("chart_asof")
            p["_chart_cache_stale"] = not _chart_cache_fresh(cached, max_age)
            q = dict(cached.get("chart_quality") or {})
            if q:
                q["24h"] = ((p.get("chart_quality") or {}).get("24h")
                            or ("real_intraday" if len(p.get("intraday") or []) > 1 else "unavailable"))
                p["chart_quality"] = q


def _cached_chart_status(row: dict, prev: dict, max_age_hours: float) -> str:
    cached = prev.get(row.get("source_symbol")) or prev.get(row.get("ticker"))
    if not cached or not cached.get("spark"):
        return "missing"
    return "fresh" if _chart_cache_fresh(cached, max_age_hours) else "stale"


def _idx_intraday_overlay(prices: dict, rows: list[dict], previous_sectors: list | None) -> None:
    """Rotate true 30-minute Yahoo charts across IDX while TradingView owns quotes."""
    limit = max(0, int(getattr(settings, "IDX_INTRADAY_BATCH_LIMIT", 0)))
    if not limit or not rows:
        return
    previous = _previous_rows(previous_sectors)

    def prior(row: dict) -> dict:
        return previous.get(row.get("source_symbol")) or previous.get(row.get("ticker")) or {}

    def priority(row: dict) -> tuple:
        cached = prior(row)
        missing = 0 if len(cached.get("intraday") or []) <= 1 else 1
        try:
            asof = float(cached.get("chart_asof") or 0)
        except Exception:  # noqa: BLE001
            asof = 0.0
        return (missing, asof, -_row_cap(row), row.get("ticker") or "")

    selected = sorted(rows, key=priority)[:limit]
    selected_symbols = {r.get("source_symbol") for r in selected}
    fetched = {}
    try:
        from tools import yquote
        fetched = yquote.fetch_intraday([r.get("source_symbol") for r in selected], workers=16)
    except Exception as e:  # noqa: BLE001
        print(f"[sectors] IDX intraday rotation failed: {e}")

    resolved = 0
    for row in rows:
        sym = row.get("source_symbol")
        current = prices.setdefault(sym, {})
        live = fetched.get(sym) if sym in selected_symbols else None
        cached = prior(row)
        source = (
            live if live and len(live.get("intraday") or []) > 1
            else cached if len(cached.get("intraday") or []) > 1
            else None
        )
        if not source:
            continue
        current["intraday"] = source.get("intraday") or []
        current["chart_asof"] = source.get("chart_asof") or cached.get("chart_asof")
        # Session bounds/state still come from the TradingView IDX calendar layer.
        quality = dict(current.get("chart_quality") or {})
        if source is live:
            quality["24h"] = "real_intraday"
        else:
            max_age = float(getattr(settings, "IDX_INTRADAY_CACHE_HOURS", 3.0))
            try:
                age_hours = (time.time() - float(source.get("chart_asof") or 0)) / 3600
            except Exception:  # noqa: BLE001
                age_hours = max_age + 1
            quality["24h"] = "cached_intraday" if age_hours <= max_age else "stale_intraday"
        current["chart_quality"] = quality
        resolved += 1
    print(f"[sectors] IDX intraday routes: {resolved}/{len(rows)} cached; {len(fetched)}/{len(selected)} refreshed")


def _broad_chart_priority(row: dict) -> tuple:
    # Other-region rows are deliberate macro benchmarks and have a much smaller
    # universe than US names; protect them from being starved by S&P/Nasdaq gaps.
    country_rank = 0 if row.get("country") not in ("US", "ID", "CR") else 1
    return (country_rank, -_row_cap(row), row.get("ticker") or "")


def collect(previous_sectors: list | None = None, telemetry: list | None = None) -> list:
    sector_rows = universe.priced_rows_by_sector()
    prices = {}
    idx_prices = {}
    if getattr(settings, "IDX_ALL_PRICE_ACTIVE", False):
        try:
            from tools import idx_membership
            idx_prices = idx_membership.price_map()
            prices.update(idx_prices)
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
    rich_rows = [r for r in all_rows
                 if r.get("data_tier") == universe.DATA_TIER_ACTIVE and not _uses_tradingview_idx(r)]
    price_only = [r for r in all_rows
                  if r.get("data_tier") != universe.DATA_TIER_ACTIVE
                  and not str(r.get("source_symbol", "")).startswith("CG:")
                  and not _uses_tradingview_idx(r)]
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

    previous_by_symbol = _previous_rows(previous_sectors)
    cache_hours = float(getattr(settings, "PRICE_ONLY_CHART_CACHE_HOURS", 36))

    chart_candidates = sorted(
        [r for r in price_only
         if not (prices.get(r["source_symbol"]) or {}).get("spark")
         and _cached_chart_status(r, previous_by_symbol, cache_hours) != "fresh"],
        key=lambda r: (
            0 if _cached_chart_status(r, previous_by_symbol, cache_hours) == "missing" else 1,
            -_row_cap(r),
        ),
    )
    chart_rows = chart_candidates[:chart_limit]
    chart_symbols = {r["source_symbol"] for r in chart_rows}
    lite_rows = [r for r in price_only
                 if r["source_symbol"] not in prices and r["source_symbol"] not in chart_symbols]

    prices.update(_batch_prices([row["source_symbol"] for row in rich_rows]))
    if chart_rows:
        from tools import yquote
        prices.update(yquote.fetch([row["source_symbol"] for row in chart_rows], workers=8))
    if lite_rows:
        from tools import yquote
        prices.update(yquote.fetch_lite([row["source_symbol"] for row in lite_rows]))
    if getattr(settings, "GLOBAL_TV_PRICE_ACTIVE", False):
        global_rows = [r for r in price_only if r.get("country") not in ("US", "ID", "CR")]
        if global_rows:
            try:
                from tools import tradingview_global
                for sym, overlay in tradingview_global.price_map(global_rows).items():
                    p = prices.setdefault(sym, {})
                    prior_quality = dict(p.get("chart_quality") or {})
                    p.update(overlay)
                    q = dict(overlay.get("chart_quality") or {})
                    if prior_quality.get("24h"):
                        q["24h"] = prior_quality["24h"]
                    p["chart_quality"] = {**prior_quality, **q}
            except Exception as e:  # noqa: BLE001
                print(f"[sectors] TradingView global overlay failed: {e}")
    _merge_cached_charts(prices, price_only, previous_sectors)
    finnhub_limit = max(0, int(getattr(settings, "PRICE_ONLY_FINNHUB_CHART_LIMIT", 0)))
    if finnhub_limit:
        missing_after_yahoo = sorted(
            [r for r in price_only if not (prices.get(r["source_symbol"]) or {}).get("spark")],
            key=_broad_chart_priority,
        )
        if missing_after_yahoo:
            try:
                from tools import finnhub
                for sym, chart in finnhub.chart_series(
                    [row["source_symbol"] for row in missing_after_yahoo],
                    limit=finnhub_limit,
                ).items():
                    prices.setdefault(sym, {}).update(chart)
                _merge_cached_charts(prices, price_only, previous_sectors)
            except Exception as e:  # noqa: BLE001
                print(f"[sectors] Finnhub chart fallback failed: {e}")
    # TradingView is the IDX source of truth for price, cap, volume, 6M spark, and screen fields.
    if idx_prices:
        prices.update(idx_prices)
        idx_rows = [r for r in all_rows if _uses_tradingview_idx(r)]
        _idx_intraday_overlay(prices, idx_rows, previous_sectors)
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
                    if p["intraday"]:
                        p["chart_asof"] = int(time.time())
                if not p.get("spark"):
                    ser = crypto_quotes.chart_series(sym, 180, "daily")
                    p["spark"] = ser["spark"][-180:]
                    p["spark_ts"] = ser["spark_ts"][-180:]
                    if p["spark"]:
                        p["chart_asof"] = int(time.time())
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
                "avg_volume_10d": _pick_price_field(p or {}, base, "avg_volume_10d"),
                "avg_volume_30d": _pick_price_field(p or {}, base, "avg_volume_30d"),
                "relative_volume_10d": _pick_price_field(p or {}, base, "relative_volume_10d"),
                "perf_1w": _pick_price_field(p or {}, base, "perf_1w"),
                "perf_1m": _pick_price_field(p or {}, base, "perf_1m"),
                "perf_3m": _pick_price_field(p or {}, base, "perf_3m"),
                "perf_6m": _pick_price_field(p or {}, base, "perf_6m"),
                "perf_ytd": _pick_price_field(p or {}, base, "perf_ytd"),
                "perf_1y": _pick_price_field(p or {}, base, "perf_1y"),
                "volatility_1w": _pick_price_field(p or {}, base, "volatility_1w"),
                "volatility_1m": _pick_price_field(p or {}, base, "volatility_1m"),
                "volatility_1d": _pick_price_field(p or {}, base, "volatility_1d"),
                "recommend_all": _pick_price_field(p or {}, base, "recommend_all"),
                "rsi": _pick_price_field(p or {}, base, "rsi"),
                "price_history_quality": _pick_price_field(p or {}, base, "price_history_quality"),
                "chart_quality": _pick_price_field(p or {}, base, "chart_quality"),
                "chart_asof": _pick_price_field(p or {}, base, "chart_asof"),
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
            fundamentals.enrich_idx_screen(rows, risk_benchmarks=risk_benchmarks)
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
