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


SCORE_SCHEMA_VERSION = 4


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


def _spark_pairs(row: dict) -> list[tuple[int | None, float]]:
    vals = [_num(x) for x in (row.get("spark") or [])]
    vals = [x for x in vals if x is not None]
    ts = row.get("spark_ts") or []
    if ts and len(ts) >= len(vals):
        ts = ts[-len(vals):]
    else:
        ts = [None] * len(vals)
    return [(ts[i], vals[i]) for i in range(len(vals))]


def _daily_returns(vals: list[float]) -> list[float]:
    out = []
    for a, b in zip(vals, vals[1:]):
        if a:
            out.append((b / a - 1))
    return out


def _risk_stats(row: dict, mode: str) -> dict:
    pairs = _spark_pairs(row)
    vals = [p[1] for p in pairs]
    if len(vals) < 12:
        return {}

    rets = _daily_returns(vals)
    periods = 365 if mode == "crypto" else 252
    sharpe = sortino = None
    if len(rets) >= 10:
        mean = statistics.fmean(rets)
        stdev = statistics.pstdev(rets)
        if stdev:
            sharpe = round((mean / stdev) * math.sqrt(periods), 2)
        downside = [r for r in rets if r < 0]
        if len(downside) >= 2:
            down_dev = statistics.pstdev(downside)
            if down_dev:
                sortino = round((mean / down_dev) * math.sqrt(periods), 2)

    peak_i = max(range(len(vals)), key=lambda i: vals[i])
    bottom_i = min(range(len(vals)), key=lambda i: vals[i])
    running_peak_i, max_dd = 0, 0.0
    dd_peak_i = dd_trough_i = 0
    for i, price in enumerate(vals):
        if price > vals[running_peak_i]:
            running_peak_i = i
        peak = vals[running_peak_i]
        if peak:
            dd = (price / peak - 1) * 100
            if dd < max_dd:
                max_dd = dd
                dd_peak_i = running_peak_i
                dd_trough_i = i

    return {
        "period": "6M daily closes",
        "risk_free_rate": 0,
        "sharpe": sharpe,
        "sortino": sortino,
        "peak_price": round(vals[peak_i], 4),
        "peak_ts": pairs[peak_i][0],
        "bottom_price": round(vals[bottom_i], 4),
        "bottom_ts": pairs[bottom_i][0],
        "max_drawdown_pct": round(max_dd, 2),
        "max_drawdown_peak_price": round(vals[dd_peak_i], 4),
        "max_drawdown_peak_ts": pairs[dd_peak_i][0],
        "max_drawdown_trough_price": round(vals[dd_trough_i], 4),
        "max_drawdown_trough_ts": pairs[dd_trough_i][0],
    }


def _metric(label: str, value, fmt: str = "number", currency: str | None = None,
            period: str | None = None) -> dict:
    out = {"label": label, "value": value, "fmt": fmt}
    if currency:
        out["currency"] = currency
    if period:
        out["period"] = period
    return out


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
    current_price = _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice"))
    return {
        "currency": info.get("financialCurrency") or info.get("currency"),
        "current_price": current_price,
        "pe": _num(info.get("trailingPE")),
        "forward_pe": _num(info.get("forwardPE")),
        "ev_ebitda": _num(info.get("enterpriseToEbitda")),
        "pb": _num(info.get("priceToBook")),
        "beta": _num(info.get("beta")),
        "eps": _num(info.get("trailingEps")),
        "book_value": _num(info.get("bookValue")),
        "roe_pct": _pct(info.get("returnOnEquity")),
        "debt_to_equity": _num(info.get("debtToEquity")),
        "revenue_growth_pct": _pct(info.get("revenueGrowth")),
        "eps_growth_pct": _pct(info.get("earningsGrowth")),
        "dividend_yield_pct": _pct(info.get("dividendYield")),
        "gross_profit": _num(info.get("grossProfits")),
        "total_cash": _num(info.get("totalCash")),
        "free_cash_flow": fcf,
        "fcf_yield_pct": fcf_yield,
        "market_cap": market_cap,
        "source": "Yahoo Finance",
        "as_of": _now_iso(),
    }


def _score_equity(row: dict, metrics: dict) -> dict:
    metrics = dict(metrics)
    metrics["_risk_stats"] = _risk_stats(row, "equity")
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
    metrics = dict(metrics)
    metrics["_risk_stats"] = _risk_stats(row, "crypto")
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
    metrics["liquidity_pct"] = round(liquidity, 2) if liquidity is not None else None
    return _pack_score("crypto", axes, metrics, one_month, six_month, vol)


def _median(vals: list[float]) -> float | None:
    vals = sorted(v for v in vals if v and v > 0)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def _valuation_components(metrics: dict, eps_multiple: float, pb_multiple: float,
                          required_fcf_yield: float) -> list[dict]:
    current = _num(metrics.get("current_price"))
    candidates = []
    eps = _num(metrics.get("eps"))
    if eps and eps > 0:
        candidates.append({
            "method": f"EPS × {eps_multiple:g} P/E",
            "price": eps * eps_multiple,
            "input": f"EPS {round(eps, 2)}",
        })

    book = _num(metrics.get("book_value"))
    roe = _num(metrics.get("roe_pct"))
    if book and book > 0:
        candidates.append({
            "method": f"Book value × {pb_multiple:g} P/B",
            "price": book * pb_multiple,
            "input": f"Book value {round(book, 2)}, ROE {round(roe, 2) if roe is not None else 'n/a'}%",
        })

    fcf_yield = _num(metrics.get("fcf_yield_pct"))
    if current and current > 0 and fcf_yield and fcf_yield > 0 and required_fcf_yield > 0:
        candidates.append({
            "method": f"Current price × FCF yield / {required_fcf_yield:g}%",
            "price": current * (fcf_yield / required_fcf_yield),
            "input": f"FCF yield {round(fcf_yield, 2)}%",
        })
    return candidates


def _valuation(metrics: dict) -> dict | None:
    """Multiple-based fair-value estimate from provider fields.

    This is intentionally conservative and transparent: it uses only inputs Yahoo
    already supplied, then reports the method and components so the UI can avoid
    treating it as a broker target price.
    """
    current = _num(metrics.get("current_price"))
    if not current or current <= 0:
        return None

    roe = _num(metrics.get("roe_pct"))
    base_pb = 2.5 if roe and roe >= 20 else 1.8 if roe and roe >= 12 else 1.2
    scenarios = [
        ("Bear", 12, max(0.8, base_pb - 0.5), 10),
        ("Base", 15, base_pb, 8),
        ("Bull", 20, base_pb + 0.7, 6),
    ]
    sensitivity = []
    base_components = []
    for name, pe_mult, pb_mult, fcf_req in scenarios:
        components = _valuation_components(metrics, pe_mult, pb_mult, fcf_req)
        target = _median([c["price"] for c in components])
        if target:
            sensitivity.append({
                "case": name,
                "target": round(target, 2),
                "upside_pct": round((target / current - 1) * 100, 2),
                "assumptions": f"P/E {pe_mult:g}x, P/B {pb_mult:g}x, required FCF yield {fcf_req:g}%",
                "components": components,
            })
        if name == "Base":
            base_components = components

    fair = next((s["target"] for s in sensitivity if s["case"] == "Base"), None)
    if not fair:
        return None

    upside = (fair / current - 1) * 100
    range_low = min(s["target"] for s in sensitivity)
    range_high = max(s["target"] for s in sensitivity)
    buy_below = fair * 0.85
    accumulate_below = fair * 0.95
    trim_above = fair * 1.15
    if upside >= 20:
        status = "Undervalued"
    elif upside <= -20:
        status = "Overvalued"
    else:
        status = "Fair value range"
    if current <= buy_below:
        signal = "Buy zone"
    elif current <= accumulate_below:
        signal = "Accumulate zone"
    elif current <= trim_above:
        signal = "Wait / fair zone"
    else:
        signal = "Expensive / trim zone"
    return {
        "status": status,
        "fair_value": round(fair, 2),
        "target_price": round(fair, 2),
        "range_low": round(range_low, 2),
        "range_high": round(range_high, 2),
        "buy_below": round(buy_below, 2),
        "accumulate_below": round(accumulate_below, 2),
        "trim_above": round(trim_above, 2),
        "signal": signal,
        "upside_pct": round(upside, 2),
        "current_price": round(current, 2),
        "currency": metrics.get("currency"),
        "components": base_components,
        "sensitivity": sensitivity,
        "note": "Model estimate from Yahoo Finance metrics; not a broker target price or investment advice.",
    }


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
    currency = metrics.get("currency") or ("USD" if mode == "crypto" else None)
    one_month_period = "30D price return" if mode == "crypto" else "22 trading sessions"
    vol_period = "daily realized, 6M window" if mode == "crypto" else "daily realized, ~6M window"
    risk = metrics.get("_risk_stats") or {}
    metric_rows = [
        _metric("Current Price", _fmt_metric_value(metrics.get("current_price"), "number"), "number", currency, "latest quote"),
        _metric("P/E", _fmt_metric_value(metrics.get("pe"), "ratio"), "ratio", period="TTM"),
        _metric("Fwd P/E", _fmt_metric_value(metrics.get("forward_pe"), "ratio"), "ratio", period="forward 12M estimate"),
        _metric("EV/EBITDA", _fmt_metric_value(metrics.get("ev_ebitda"), "ratio"), "ratio", period="TTM"),
        _metric("P/B", _fmt_metric_value(metrics.get("pb"), "ratio"), "ratio", period="latest book value"),
        _metric("Book Value", _fmt_metric_value(metrics.get("book_value"), "number"), "number", currency, "per share, latest quarter"),
        _metric("Beta", _fmt_metric_value(metrics.get("beta"), "ratio"), "ratio", period="5Y monthly"),
        _metric("EPS", _fmt_metric_value(metrics.get("eps"), "number"), "number", currency, "TTM"),
        _metric("ROE", _fmt_metric_value(metrics.get("roe_pct"), "percent"), "percent", period="TTM"),
        _metric("Debt/Equity", _fmt_metric_value(metrics.get("debt_to_equity"), "percent"), "percent", period="latest quarter"),
        _metric("Revenue Growth", _fmt_metric_value(metrics.get("revenue_growth_pct"), "percent"), "percent", period="YoY quarterly"),
        _metric("EPS Growth", _fmt_metric_value(metrics.get("eps_growth_pct"), "percent"), "percent", period="YoY quarterly"),
        _metric("Dividend Yield", _fmt_metric_value(metrics.get("dividend_yield_pct"), "percent"), "percent", period="forward annual"),
        _metric("Gross Profit", _fmt_metric_value(metrics.get("gross_profit"), "money"), "money", currency, "TTM"),
        _metric("Total Cash", _fmt_metric_value(metrics.get("total_cash"), "money"), "money", currency, "latest quarter"),
        _metric("Free Cash Flow", _fmt_metric_value(metrics.get("free_cash_flow"), "money"), "money", currency, "TTM"),
        _metric("FCF Yield", _fmt_metric_value(metrics.get("fcf_yield_pct"), "percent"), "percent", period="TTM FCF / market cap"),
        _metric("Market Cap", _fmt_metric_value(metrics.get("market_cap"), "money"), "money", currency, "latest quote"),
        _metric("24h Volume", _fmt_metric_value(metrics.get("volume_24h"), "money"), "money", currency, "24H"),
        _metric("Liquidity", _fmt_metric_value(metrics.get("liquidity_pct"), "percent"), "percent", period="24H volume / market cap"),
        _metric("1M Return", one_month, "percent", period=one_month_period),
        _metric("6M Return", six_month, "percent", period="6M price return"),
        _metric("Volatility", vol, "percent", period=vol_period),
        _metric("Sharpe Ratio", _fmt_metric_value(risk.get("sharpe"), "ratio"), "ratio", period="annualized, 0% RF, 6M daily"),
        _metric("Sortino Ratio", _fmt_metric_value(risk.get("sortino"), "ratio"), "ratio", period="annualized downside, 0% RF, 6M daily"),
        _metric("Max Drawdown", _fmt_metric_value(risk.get("max_drawdown_pct"), "percent"), "percent", period="peak-to-trough, 6M"),
    ]
    return {
        "mode": mode,
        "schema_version": SCORE_SCHEMA_VERSION,
        "score": overall,
        "label": label,
        "coverage": round(len(valid) / len(axes), 2),
        "axes": axes,
        "metrics": [m for m in metric_rows if m["value"] is not None],
        "valuation": _valuation(metrics) if mode == "equity" else None,
        "risk_stats": risk or None,
        "currency": currency,
        "source": metrics.get("source") or ("CoinGecko + price history" if mode == "crypto" else "Yahoo Finance"),
        "as_of": metrics.get("as_of") or _now_iso(),
    }


def _previous_metrics(previous_by_symbol: dict, row: dict, ttl_hours: int) -> dict | None:
    prev = previous_by_symbol.get(row.get("source_symbol")) or previous_by_symbol.get(row.get("ticker"))
    fs = (prev or {}).get("fundamental_score") or {}
    if fs.get("schema_version") != SCORE_SCHEMA_VERSION:
        return None
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
            "Current Price": "current_price",
            "P/E": "pe", "Fwd P/E": "forward_pe", "EV/EBITDA": "ev_ebitda",
            "P/B": "pb", "Book Value": "book_value", "Beta": "beta", "EPS": "eps", "ROE": "roe_pct",
            "Debt/Equity": "debt_to_equity", "Revenue Growth": "revenue_growth_pct",
            "EPS Growth": "eps_growth_pct", "Dividend Yield": "dividend_yield_pct",
            "Gross Profit": "gross_profit", "Total Cash": "total_cash",
            "Free Cash Flow": "free_cash_flow", "FCF Yield": "fcf_yield_pct", "Market Cap": "market_cap",
            "24h Volume": "volume_24h", "Liquidity": "liquidity_pct",
        }.get(label)
        if key:
            metrics[key] = value
    if metrics:
        metrics["currency"] = fs.get("currency")
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
                ], {"source": "Price history only", "as_of": _now_iso(),
                    "_risk_stats": _risk_stats(row, "equity")},
                _spark_return(row.get("spark"), 22), _spark_return(row.get("spark")),
                _spark_volatility(row.get("spark")))
