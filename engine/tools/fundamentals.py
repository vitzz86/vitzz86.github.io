"""Ticker-level investment scoring.

Uses real provider fields only. Equity metrics come from Yahoo Finance/yfinance
when available; crypto uses live CoinGecko-derived price/liquidity fields plus
chart momentum. Missing metrics stay null and reduce coverage instead of being
filled with model guesses.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import math
import statistics


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str | None) -> dt.datetime | None:
    try:
        return dt.datetime.strptime(s or "", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def _num(v):
    try:
        if v is None:
            return None
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:  # noqa: BLE001
        return None


def _pct(v):
    x = _num(v)
    if x is None:
        return None
    return round(x * 100, 2) if abs(x) <= 3 else round(x, 2)


def _score_low(v, good: float, bad: float):
    v = _num(v)
    if v is None or v <= 0:
        return None
    if v <= good:
        return 100
    if v >= bad:
        return 0
    return round(100 - ((v - good) / (bad - good) * 100))


def _score_high(v, bad: float, good: float):
    v = _num(v)
    if v is None:
        return None
    if v <= bad:
        return 0
    if v >= good:
        return 100
    return round((v - bad) / (good - bad) * 100)


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals)) if vals else None


def _spark_return(spark: list, days: int = None):
    vals = [_num(x) for x in (spark or []) if _num(x) is not None]
    if len(vals) < 2:
        return None
    if days and len(vals) > days:
        vals = vals[-days:]
    if not vals[0]:
        return None
    return round((vals[-1] / vals[0] - 1) * 100, 2)


def _spark_volatility(spark: list):
    vals = [_num(x) for x in (spark or []) if _num(x) is not None]
    if len(vals) < 12:
        return None
    rets = []
    for a, b in zip(vals, vals[1:]):
        if a:
            rets.append((b / a - 1) * 100)
    if len(rets) < 10:
        return None
    return round(statistics.pstdev(rets), 2)


def _metric(label: str, value, fmt: str = "number") -> dict:
    return {"label": label, "value": value, "fmt": fmt}


def _fmt_metric_value(v, fmt: str):
    if v is None:
        return None
    if fmt == "percent":
        return round(float(v), 2)
    if fmt == "ratio":
        return round(float(v), 2)
    if fmt == "money":
        return round(float(v), 0)
    return round(float(v), 2)


def _fetch_equity(sym: str) -> dict:
    import yfinance as yf

    info = yf.Ticker(sym).get_info() or {}
    market_cap = _num(info.get("marketCap"))
    fcf = _num(info.get("freeCashflow"))
    fcf_yield = round(fcf / market_cap * 100, 2) if fcf and market_cap else None
    return {
        "pe": _num(info.get("trailingPE")),
        "forward_pe": _num(info.get("forwardPE")),
        "ev_ebitda": _num(info.get("enterpriseToEbitda")),
        "pb": _num(info.get("priceToBook")),
        "roe_pct": _pct(info.get("returnOnEquity")),
        "debt_to_equity": _num(info.get("debtToEquity")),
        "revenue_growth_pct": _pct(info.get("revenueGrowth")),
        "eps_growth_pct": _pct(info.get("earningsGrowth")),
        "dividend_yield_pct": _pct(info.get("dividendYield")),
        "fcf_yield_pct": fcf_yield,
        "market_cap": market_cap,
        "source": "Yahoo Finance",
        "as_of": _now_iso(),
    }


def _score_equity(row: dict, metrics: dict) -> dict:
    one_month = _spark_return(row.get("spark"), 22)
    six_month = _spark_return(row.get("spark"))
    vol = _spark_volatility(row.get("spark"))
    value = _avg([
        _score_low(metrics.get("forward_pe") or metrics.get("pe"), 12, 45),
        _score_low(metrics.get("pb"), 1.5, 8),
        _score_low(metrics.get("ev_ebitda"), 8, 25),
        _score_high(metrics.get("fcf_yield_pct"), 0, 8),
        _score_high(metrics.get("dividend_yield_pct"), 0, 5),
    ])
    quality = _avg([
        _score_high(metrics.get("roe_pct"), 0, 25),
        _score_low(metrics.get("debt_to_equity"), 40, 250),
        _score_high(metrics.get("fcf_yield_pct"), 0, 8),
    ])
    growth = _avg([
        _score_high(metrics.get("revenue_growth_pct"), -5, 25),
        _score_high(metrics.get("eps_growth_pct"), -10, 30),
    ])
    momentum = _avg([
        _score_high(row.get("delta_pct"), -3, 3),
        _score_high(one_month, -8, 12),
        _score_high(six_month, -20, 35),
    ])
    risk = _avg([
        _score_low(vol, 1.2, 5.0),
        _score_low(metrics.get("debt_to_equity"), 40, 250),
        _score_high(six_month, -35, 15),
    ])
    axes = [
        {"key": "value", "label": "Value", "score": value},
        {"key": "quality", "label": "Quality", "score": quality},
        {"key": "growth", "label": "Growth", "score": growth},
        {"key": "momentum", "label": "Momentum", "score": momentum},
        {"key": "risk", "label": "Risk", "score": risk},
    ]
    return _pack_score("equity", axes, metrics, one_month, six_month, vol)


def _score_crypto(row: dict, metrics: dict) -> dict:
    one_month = _spark_return(row.get("spark"), 30)
    six_month = _spark_return(row.get("spark"))
    vol = _spark_volatility(row.get("spark"))
    market_cap = metrics.get("market_cap")
    volume = metrics.get("volume_24h") or row.get("turnover")
    liquidity = (volume / market_cap * 100) if volume and market_cap else None
    axes = [
        {"key": "size", "label": "Size", "score": _score_high(market_cap, 1_000_000_000, 100_000_000_000)},
        {"key": "liquidity", "label": "Liquidity", "score": _score_high(liquidity, 0.5, 8)},
        {"key": "momentum", "label": "Momentum", "score": _avg([
            _score_high(row.get("delta_pct"), -5, 5),
            _score_high(one_month, -15, 25),
        ])},
        {"key": "trend", "label": "Trend", "score": _score_high(six_month, -40, 80)},
        {"key": "risk", "label": "Risk", "score": _score_low(vol, 2.5, 9.0)},
    ]
    metrics = dict(metrics)
    metrics["liquidity_pct"] = round(liquidity, 2) if liquidity is not None else None
    return _pack_score("crypto", axes, metrics, one_month, six_month, vol)


def _pack_score(mode: str, axes: list[dict], metrics: dict, one_month, six_month, vol) -> dict:
    valid = [a["score"] for a in axes if a.get("score") is not None]
    overall = round(sum(valid) / len(valid)) if valid else None
    if overall is None:
        label = "Insufficient"
    elif overall >= 75:
        label = "Strong"
    elif overall >= 60:
        label = "Watchlist"
    elif overall >= 45:
        label = "Neutral"
    else:
        label = "Weak"
    metric_rows = [
        _metric("P/E", _fmt_metric_value(metrics.get("pe"), "ratio"), "ratio"),
        _metric("Fwd P/E", _fmt_metric_value(metrics.get("forward_pe"), "ratio"), "ratio"),
        _metric("P/B", _fmt_metric_value(metrics.get("pb"), "ratio"), "ratio"),
        _metric("ROE", _fmt_metric_value(metrics.get("roe_pct"), "percent"), "percent"),
        _metric("Debt/Equity", _fmt_metric_value(metrics.get("debt_to_equity"), "ratio"), "ratio"),
        _metric("Revenue Growth", _fmt_metric_value(metrics.get("revenue_growth_pct"), "percent"), "percent"),
        _metric("EPS Growth", _fmt_metric_value(metrics.get("eps_growth_pct"), "percent"), "percent"),
        _metric("Dividend Yield", _fmt_metric_value(metrics.get("dividend_yield_pct"), "percent"), "percent"),
        _metric("FCF Yield", _fmt_metric_value(metrics.get("fcf_yield_pct"), "percent"), "percent"),
        _metric("Market Cap", _fmt_metric_value(metrics.get("market_cap"), "money"), "money"),
        _metric("24h Volume", _fmt_metric_value(metrics.get("volume_24h"), "money"), "money"),
        _metric("Liquidity", _fmt_metric_value(metrics.get("liquidity_pct"), "percent"), "percent"),
        _metric("1M Return", one_month, "percent"),
        _metric("6M Return", six_month, "percent"),
        _metric("Volatility", vol, "percent"),
    ]
    return {
        "mode": mode,
        "score": overall,
        "label": label,
        "coverage": round(len(valid) / len(axes), 2),
        "axes": axes,
        "metrics": [m for m in metric_rows if m["value"] is not None],
        "source": metrics.get("source") or ("CoinGecko + price history" if mode == "crypto" else "Yahoo Finance"),
        "as_of": metrics.get("as_of") or _now_iso(),
    }


def _previous_metrics(previous_by_symbol: dict, row: dict, ttl_hours: int) -> dict | None:
    prev = previous_by_symbol.get(row.get("source_symbol")) or previous_by_symbol.get(row.get("ticker"))
    fs = (prev or {}).get("fundamental_score") or {}
    as_of = _parse_iso(fs.get("as_of"))
    if not as_of:
        return None
    age_h = (dt.datetime.now(dt.timezone.utc) - as_of).total_seconds() / 3600
    if age_h > ttl_hours:
        return None
    metrics = {}
    for m in fs.get("metrics") or []:
        label = m.get("label")
        value = m.get("value")
        key = {
            "P/E": "pe", "Fwd P/E": "forward_pe", "P/B": "pb", "ROE": "roe_pct",
            "Debt/Equity": "debt_to_equity", "Revenue Growth": "revenue_growth_pct",
            "EPS Growth": "eps_growth_pct", "Dividend Yield": "dividend_yield_pct",
            "FCF Yield": "fcf_yield_pct", "Market Cap": "market_cap",
            "24h Volume": "volume_24h", "Liquidity": "liquidity_pct",
        }.get(label)
        if key:
            metrics[key] = value
    if metrics:
        metrics["source"] = fs.get("source")
        metrics["as_of"] = fs.get("as_of")
        return metrics
    return None


def enrich(rows: list[dict], previous_by_symbol: dict | None = None,
           refresh_hours: int = 24, workers: int = 6) -> None:
    previous_by_symbol = previous_by_symbol or {}
    to_fetch, metric_cache = [], {}
    for row in rows:
        sym = row.get("source_symbol")
        if not sym:
            continue
        if row.get("country") == "CR":
            metric_cache[sym] = {
                "market_cap": row.get("market_cap_value"),
                "volume_24h": row.get("volume_24h"),
                "source": "CoinGecko + price history",
                "as_of": _now_iso(),
            }
            continue
        cached = _previous_metrics(previous_by_symbol, row, refresh_hours)
        if cached:
            metric_cache[sym] = cached
        else:
            to_fetch.append(sym)

    uniq = list(dict.fromkeys(to_fetch))
    if uniq:
        try:
            with cf.ThreadPoolExecutor(max_workers=workers) as ex:
                for sym, metrics in zip(uniq, ex.map(_fetch_equity, uniq)):
                    if metrics:
                        metric_cache[sym] = metrics
        except Exception as e:  # noqa: BLE001
            print(f"[fundamentals] equity fetch failed: {e}")

    for row in rows:
        metrics = metric_cache.get(row.get("source_symbol")) or {}
        if row.get("country") == "CR":
            row["fundamental_score"] = _score_crypto(row, metrics)
        else:
            row["fundamental_score"] = _score_equity(row, metrics) if metrics else _pack_score(
                "equity", [
                    {"key": "value", "label": "Value", "score": None},
                    {"key": "quality", "label": "Quality", "score": None},
                    {"key": "growth", "label": "Growth", "score": None},
                    {"key": "momentum", "label": "Momentum", "score": _avg([
                        _score_high(row.get("delta_pct"), -3, 3),
                        _score_high(_spark_return(row.get("spark"), 22), -8, 12),
                        _score_high(_spark_return(row.get("spark")), -20, 35),
                    ])},
                    {"key": "risk", "label": "Risk", "score": _score_low(_spark_volatility(row.get("spark")), 1.2, 5.0)},
                ], {"source": "Price history only", "as_of": _now_iso()},
                _spark_return(row.get("spark"), 22), _spark_return(row.get("spark")),
                _spark_volatility(row.get("spark")))
