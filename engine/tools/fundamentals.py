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


SCORE_SCHEMA_VERSION = 8


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


def _risk_context(row: dict, mode: str, benchmarks: dict | None = None) -> dict:
    benchmarks = benchmarks or {}
    key = "CR" if mode == "crypto" else (row.get("country") or "US")
    ctx = dict(benchmarks.get(key) or benchmarks.get("US") or {})
    rf = _num(ctx.get("risk_free_rate"))
    if rf is None:
        rf = _num(ctx.get("hurdle_rate"))
        if rf is not None:
            ctx["risk_free_label"] = ctx.get("hurdle_label") or ctx.get("risk_free_label")
            ctx["risk_free_source"] = ctx.get("hurdle_source") or ctx.get("risk_free_source")
    if rf is None and key != "US":
        us = benchmarks.get("US") or {}
        rf = _num(us.get("risk_free_rate")) or _num(us.get("hurdle_rate"))
        if rf is not None:
            ctx["risk_free_label"] = us.get("risk_free_label") or us.get("hurdle_label")
            ctx["risk_free_source"] = us.get("risk_free_source") or us.get("hurdle_source")
            ctx["risk_free_symbol"] = us.get("risk_free_symbol")
    if rf is None:
        rf = 0.0
        ctx.setdefault("risk_free_label", "0% fallback")
        ctx.setdefault("risk_free_source", "fallback")
    ctx["risk_free_rate"] = rf
    ctx.setdefault("risk_free_label", "Risk-free rate")
    ctx["fx_rates"] = dict(benchmarks.get("fx_rates") or {})
    hurdle = _num(ctx.get("hurdle_rate"))
    ctx["hurdle_rate"] = hurdle if hurdle is not None else rf
    ctx.setdefault("hurdle_label", ctx.get("risk_free_label", "Risk-free rate"))
    return ctx


def _risk_signal(sharpe, sortino, max_dd) -> str:
    s = _num(sharpe)
    so = _num(sortino)
    dd = _num(max_dd)
    if s is None and so is None:
        return "Insufficient risk history"
    if (s is not None and s >= 1.0) and (so is None or so >= 1.2) and (dd is None or dd >= -25):
        return "Attractive risk-adjusted"
    if (s is not None and s >= 0.35) and (dd is None or dd >= -40):
        return "Fair risk-adjusted"
    if s is not None and s < 0:
        return "Weak risk-adjusted"
    return "High volatility / size carefully"


def _risk_stats(row: dict, mode: str, risk_context: dict | None = None) -> dict:
    pairs = _spark_pairs(row)
    vals = [p[1] for p in pairs]
    if len(vals) < 12:
        return {}

    rets = _daily_returns(vals)
    periods = 365 if mode == "crypto" else 252
    ctx = risk_context or {}
    rf = _num(ctx.get("risk_free_rate")) or 0.0
    daily_rf = (1 + rf / 100) ** (1 / periods) - 1 if rf > -99 else 0.0
    sharpe = sortino = annual_return = annual_excess = annual_vol = downside_vol = None
    if len(rets) >= 10:
        excess = [r - daily_rf for r in rets]
        mean = statistics.fmean(excess)
        stdev = statistics.pstdev(rets)
        if stdev:
            sharpe = round((mean / stdev) * math.sqrt(periods), 2)
            annual_vol = round(stdev * math.sqrt(periods) * 100, 2)
        downside = [r for r in excess if r < 0]
        if len(downside) >= 2:
            down_dev = statistics.pstdev(downside)
            if down_dev:
                sortino = round((mean / down_dev) * math.sqrt(periods), 2)
                downside_vol = round(down_dev * math.sqrt(periods) * 100, 2)
        if vals[0] > 0:
            years = max((len(vals) - 1) / periods, 1 / periods)
            annual_return = round(((vals[-1] / vals[0]) ** (1 / years) - 1) * 100, 2)
            annual_excess = round(annual_return - rf, 2)

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
        "risk_free_rate": round(rf, 3),
        "risk_free_label": ctx.get("risk_free_label"),
        "risk_free_symbol": ctx.get("risk_free_symbol"),
        "risk_free_source": ctx.get("risk_free_source"),
        "hurdle_rate": round(_num(ctx.get("hurdle_rate")) or rf, 3),
        "hurdle_label": ctx.get("hurdle_label"),
        "hurdle_source": ctx.get("hurdle_source"),
        "annual_return_pct": annual_return,
        "annual_excess_return_pct": annual_excess,
        "annual_volatility_pct": annual_vol,
        "downside_volatility_pct": downside_vol,
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
        "risk_adjusted_signal": _risk_signal(sharpe, sortino, round(max_dd, 2)),
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


def _fx_factor(src: str | None, dst: str | None, fx_rates: dict | None) -> float | None:
    src = (src or "").upper()
    dst = (dst or "").upper()
    fx_rates = fx_rates or {}
    if not src or not dst or src == dst:
        return 1.0
    usdidr = _num(fx_rates.get("USDIDR"))
    if not usdidr:
        return None
    if src == "USD" and dst == "IDR":
        return usdidr
    if src == "IDR" and dst == "USD":
        return 1 / usdidr
    return None


def _sanitize_ratio(v, max_reasonable: float = 500.0):
    x = _num(v)
    if x is None or abs(x) > max_reasonable:
        return None
    return x


def _fetch_equity(sym: str) -> dict:
    import yfinance as yf

    info = yf.Ticker(sym).get_info() or {}
    quote_currency = info.get("currency") or ("IDR" if sym.endswith(".JK") else None)
    financial_currency = info.get("financialCurrency") or quote_currency
    market_cap = _num(info.get("marketCap"))
    fcf = _num(info.get("freeCashflow"))
    fcf_yield = round(fcf / market_cap * 100, 2) if fcf and market_cap else None
    current_price = _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice"))
    return {
        "currency": quote_currency or financial_currency,
        "quote_currency": quote_currency or financial_currency,
        "financial_currency": financial_currency or quote_currency,
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


def _normalize_currencies(row: dict, metrics: dict, risk_context: dict | None = None) -> dict:
    metrics = dict(metrics)
    quote_currency = (metrics.get("quote_currency") or metrics.get("currency")
                      or ("IDR" if row.get("country") == "ID" else None))
    financial_currency = metrics.get("financial_currency") or quote_currency
    if row.get("country") == "ID" and row.get("exchange") == "IDX":
        quote_currency = "IDR"
    metrics["currency"] = quote_currency
    metrics["quote_currency"] = quote_currency
    metrics["financial_currency"] = financial_currency

    if _num(row.get("value")):
        metrics["current_price"] = _num(row.get("value"))

    factor = _fx_factor(financial_currency, quote_currency, (risk_context or {}).get("fx_rates"))
    needs_conversion = (financial_currency and quote_currency
                        and financial_currency != quote_currency and factor)
    converted_fields = []
    if needs_conversion:
        current = _num(metrics.get("current_price"))
        for key in ("gross_profit", "total_cash", "free_cash_flow"):
            val = _num(metrics.get(key))
            if val is not None:
                metrics[key] = val * factor
                converted_fields.append(key)
        for key in ("book_value", "eps"):
            val = _num(metrics.get(key))
            # Some Yahoo non-US per-share fields are already quote-currency-like
            # despite financialCurrency being different. Convert only tiny values
            # that are clearly not on the same scale as the traded share price.
            converted = val * factor if val is not None else None
            scale = abs(converted / current) if converted is not None and current else None
            if val is not None and scale is not None and 0.01 <= scale <= 100:
                metrics[key] = converted
                converted_fields.append(key)
        metrics["_conversion_note"] = (
            f" · converted from {financial_currency} to {quote_currency} "
            f"using USD/IDR {factor:,.2f}" if financial_currency == "USD" and quote_currency == "IDR"
            else f" · converted from {financial_currency} to {quote_currency}"
        )
        metrics["_converted_fields"] = converted_fields

    current = _num(metrics.get("current_price"))
    eps = _num(metrics.get("eps"))
    book = _num(metrics.get("book_value"))
    market_cap = _num(metrics.get("market_cap"))
    fcf = _num(metrics.get("free_cash_flow"))
    metrics["pe"] = round(current / eps, 2) if current and eps and eps > 0 else _sanitize_ratio(metrics.get("pe"))
    metrics["pb"] = round(current / book, 2) if current and book and book > 0 else _sanitize_ratio(metrics.get("pb"))
    metrics["ev_ebitda"] = _sanitize_ratio(metrics.get("ev_ebitda"), 300.0)
    metrics["fcf_yield_pct"] = round(fcf / market_cap * 100, 2) if fcf and market_cap else metrics.get("fcf_yield_pct")
    return metrics


def _score_equity(row: dict, metrics: dict, risk_context: dict | None = None) -> dict:
    metrics = _normalize_currencies(row, metrics, risk_context)
    metrics["_risk_context"] = risk_context or {}
    metrics["_risk_stats"] = _risk_stats(row, "equity", risk_context)
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


def _score_crypto(row: dict, metrics: dict, risk_context: dict | None = None) -> dict:
    metrics = dict(metrics)
    metrics["_risk_context"] = risk_context or {}
    metrics["_risk_stats"] = _risk_stats(row, "crypto", risk_context)
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


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _valuation_hurdle(metrics: dict) -> float | None:
    risk = metrics.get("_risk_stats") or {}
    ctx = metrics.get("_risk_context") or {}
    return (_num(risk.get("hurdle_rate")) or _num(ctx.get("hurdle_rate"))
            or _num(risk.get("risk_free_rate")) or _num(ctx.get("risk_free_rate")))


def _growth_anchor(metrics: dict) -> float | None:
    vals = []
    for key in ("revenue_growth_pct", "eps_growth_pct"):
        v = _num(metrics.get(key))
        if v is not None and -80 <= v <= 150:
            vals.append(v)
    return round(statistics.fmean(vals), 2) if vals else None


def _fair_pe_model(metrics: dict) -> dict:
    """Dynamic fair P/E based on real provider metrics and risk context."""
    current_pe = _sanitize_ratio(metrics.get("pe"), 150.0)
    forward_pe = _sanitize_ratio(metrics.get("forward_pe"), 150.0)
    sector_pe = _sanitize_ratio(metrics.get("_sector_peer_pe"), 150.0)
    sector_scope = metrics.get("_sector_peer_pe_scope") or "sector peer median"
    roe = _num(metrics.get("roe_pct"))
    debt = _num(metrics.get("debt_to_equity"))
    fcf_yield = _num(metrics.get("fcf_yield_pct"))
    beta = _num(metrics.get("beta"))
    growth = _growth_anchor(metrics)
    risk = metrics.get("_risk_stats") or {}
    max_dd = _num(risk.get("max_drawdown_pct"))
    hurdle = _valuation_hurdle(metrics)

    hurdle_base = _clamp(100 / ((hurdle or 5.0) + 2.0), 8.0, 18.0)
    if sector_pe is not None:
        base = _clamp(sector_pe, 6.0, 35.0)
        base_label = "Base Sector P/E"
        base_note = sector_scope
    else:
        base = hurdle_base
        base_label = "Base Hurdle P/E"
        base_note = f"hurdle {hurdle:.2f}%" if hurdle is not None else "fallback rate anchor"
    adjustments: list[float] = []
    drivers: list[str] = []
    scorecard: list[dict] = [{
        "label": base_label,
        "metric": base_note,
        "value": round(base, 2),
        "adjustment": None,
    }]

    def add_adjustment(label: str, metric: str, adj: float, note: str) -> None:
        adjustments.append(adj)
        scorecard.append({
            "label": label,
            "metric": metric,
            "adjustment": round(adj, 2),
            "note": note,
        })

    if roe is not None:
        adj = _clamp((roe - 12) / 15 * 4, -3.0, 5.0)
        add_adjustment("Quality Adjustment", f"ROE {roe:.1f}%", adj,
                       "higher ROE earns a premium; weak ROE cuts the multiple")
        drivers.append(f"ROE {roe:.1f}% {'raises' if adj >= 0 else 'cuts'} fair P/E by {abs(adj):.1f}x")

    if growth is not None:
        adj = _clamp((growth - 5) / 20 * 5, -3.0, 6.0)
        add_adjustment("Growth Adjustment", f"revenue/EPS growth {growth:.1f}%", adj,
                       "growth above 5% expands the fair multiple")
        drivers.append(f"growth {growth:.1f}% {'raises' if adj >= 0 else 'cuts'} fair P/E by {abs(adj):.1f}x")

    if fcf_yield is not None:
        if fcf_yield >= 8:
            adj = 2.0
        elif fcf_yield >= 4:
            adj = 1.0
        elif fcf_yield <= 0:
            adj = -3.0
        elif fcf_yield < 2:
            adj = -1.0
        else:
            adj = 0.0
        add_adjustment("Cash-Flow Adjustment", f"FCF yield {fcf_yield:.1f}%", adj,
                       "strong FCF yield supports a higher fair P/E")
        drivers.append(f"FCF yield {fcf_yield:.1f}% {'supports' if adj >= 0 else 'pressures'} fair P/E")

    if debt is not None:
        if debt <= 40:
            adj = 1.0
        elif debt <= 100:
            adj = 0.0
        else:
            adj = -_clamp((debt - 100) / 150 * 4, 0.5, 5.0)
        add_adjustment("Balance-Sheet Adjustment", f"Debt/Equity {debt:.1f}%", adj,
                       "lower leverage improves valuation durability")
        drivers.append(f"Debt/Equity {debt:.1f}% {'supports' if adj >= 0 else 'cuts'} the multiple")

    if beta is not None:
        if beta <= 0.8:
            adj = 1.0
        elif beta <= 1.2:
            adj = 0.0
        else:
            adj = -_clamp((beta - 1.2) / 0.8 * 3, 0.5, 3.5)
        add_adjustment("Market-Risk Adjustment", f"Beta {beta:.2f}x", adj,
                       "higher beta reduces the risk-adjusted fair multiple")
        drivers.append(f"beta {beta:.2f}x {'supports' if adj >= 0 else 'cuts'} risk-adjusted fair P/E")

    if max_dd is not None:
        dd = abs(max_dd)
        if dd <= 20:
            adj = 1.0
        elif dd <= 35:
            adj = 0.0
        else:
            adj = -_clamp((dd - 35) / 25 * 3, 0.5, 4.0)
        add_adjustment("Drawdown Adjustment", f"6M max drawdown {dd:.1f}%", adj,
                       "large peak-to-trough loss lowers the fair multiple")
        drivers.append(f"6M drawdown {dd:.1f}% {'supports' if adj >= 0 else 'cuts'} the risk multiple")

    if forward_pe is not None and current_pe is not None:
        if forward_pe < current_pe * 0.85 and (growth or 0) > 0:
            add_adjustment("Forward-Earnings Adjustment", f"Fwd P/E {forward_pe:.1f}x vs current {current_pe:.1f}x", 1.0,
                           "forward earnings imply multiple compression")
            drivers.append(f"forward P/E {forward_pe:.1f}x is below current {current_pe:.1f}x")
        elif forward_pe > current_pe * 1.15:
            add_adjustment("Forward-Earnings Adjustment", f"Fwd P/E {forward_pe:.1f}x vs current {current_pe:.1f}x", -1.0,
                           "forward earnings imply multiple expansion risk")
            drivers.append(f"forward P/E {forward_pe:.1f}x is above current {current_pe:.1f}x")

    pre_cap_fair_pe = base + sum(adjustments)
    fair_pe = pre_cap_fair_pe
    cap_note = None
    if current_pe is not None:
        if (growth or 0) >= 20 and (roe or 0) >= 12:
            premium_cap = 1.55
        elif (growth or 0) >= 8 or (roe or 0) >= 18:
            premium_cap = 1.40
        else:
            premium_cap = 1.25
        upper = min(40.0, current_pe * premium_cap)
        lower = max(5.0, current_pe * 0.55)
        fair_pe = _clamp(fair_pe, lower, max(lower, upper))
        if round(fair_pe, 2) != round(pre_cap_fair_pe, 2):
            cap_note = f"bounded to {lower:.1f}x-{upper:.1f}x from current P/E {current_pe:.1f}x"
    else:
        fair_pe = _clamp(fair_pe, 5.0, 35.0)
        if round(fair_pe, 2) != round(pre_cap_fair_pe, 2):
            cap_note = "bounded to 5.0x-35.0x because current P/E is unavailable"

    if cap_note:
        scorecard.append({
            "label": "Current-Multiple Guardrail",
            "metric": cap_note,
            "adjustment": round(fair_pe - pre_cap_fair_pe, 2),
            "note": "prevents the model from drifting too far from traded valuation",
        })
    scorecard.append({
        "label": "Final Fair P/E",
        "metric": "base + adjustments",
        "value": round(fair_pe, 2),
        "adjustment": None,
    })

    pe_gap = round((fair_pe / current_pe - 1) * 100, 2) if current_pe else None
    return {
        "fair_pe": round(fair_pe, 2),
        "current_pe": round(current_pe, 2) if current_pe is not None else None,
        "forward_pe": round(forward_pe, 2) if forward_pe is not None else None,
        "base_pe": round(base, 2),
        "base_pe_source": base_note,
        "pre_guardrail_fair_pe": round(pre_cap_fair_pe, 2),
        "pe_gap_pct": pe_gap,
        "hurdle_rate": round(hurdle, 2) if hurdle is not None else None,
        "drivers": drivers[:6],
        "scorecard": scorecard,
    }


def _fair_pb(metrics: dict) -> float:
    roe = _num(metrics.get("roe_pct"))
    if roe is None:
        return 1.5
    return round(_clamp(1.0 + max(0.0, roe - 8) / 12, 0.8, 3.5), 2)


def _required_fcf_yield(metrics: dict) -> float:
    hurdle = _valuation_hurdle(metrics)
    return round(_clamp((hurdle or 5.0) + 2.0, 6.0, 12.0), 2)


def _valuation_components(metrics: dict, eps_multiple: float, pb_multiple: float,
                          required_fcf_yield: float) -> list[dict]:
    current = _num(metrics.get("current_price"))
    candidates = []
    eps = _num(metrics.get("eps"))
    current_pe = _sanitize_ratio(metrics.get("pe"), 150.0)
    forward_pe = _sanitize_ratio(metrics.get("forward_pe"), 150.0)
    if eps and eps > 0:
        candidates.append({
            "method": f"EPS × {eps_multiple:g} fair P/E",
            "price": eps * eps_multiple,
            "input": (
                f"EPS {round(eps, 2)}, current P/E "
                f"{round(current_pe, 2) if current_pe is not None else 'n/a'}x"
            ),
        })

    if current and current > 0 and forward_pe and forward_pe > 0:
        forward_eps = current / forward_pe
        candidates.append({
            "method": f"Forward EPS × {eps_multiple:g} fair P/E",
            "price": forward_eps * eps_multiple,
            "input": f"implied forward EPS {round(forward_eps, 2)}, forward P/E {round(forward_pe, 2)}x",
        })

    book = _num(metrics.get("book_value"))
    if book and book > 0:
        roe = _num(metrics.get("roe_pct"))
        current_pb = _sanitize_ratio(metrics.get("pb"), 80.0)
        # P/B is useful for banks, asset-heavy firms, and ordinary balance
        # sheets, but it badly understates asset-light compounders.
        use_pb = current_pb is None or current_pb <= 8 or (roe is not None and roe <= 20)
        if use_pb:
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

    pe_model = _fair_pe_model(metrics)
    base_pe = pe_model["fair_pe"]
    base_pb = _fair_pb(metrics)
    base_fcf_req = _required_fcf_yield(metrics)
    scenarios = [
        ("Bear", round(max(5.0, base_pe * 0.8), 2), round(max(0.7, base_pb * 0.75), 2), round(min(15.0, base_fcf_req * 1.25), 2)),
        ("Base", base_pe, base_pb, base_fcf_req),
        ("Bull", round(min(45.0, base_pe * 1.25), 2), round(min(5.0, base_pb * 1.25), 2), round(max(4.0, base_fcf_req * 0.8), 2)),
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
                "assumptions": f"fair P/E {pe_mult:g}x, P/B {pb_mult:g}x, required FCF yield {fcf_req:g}%",
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
        "valuation_model": "dynamic_fair_pe",
        "current_pe": pe_model.get("current_pe"),
        "forward_pe": pe_model.get("forward_pe"),
        "base_pe": pe_model.get("base_pe"),
        "base_pe_source": pe_model.get("base_pe_source"),
        "fair_pe": pe_model.get("fair_pe"),
        "pre_guardrail_fair_pe": pe_model.get("pre_guardrail_fair_pe"),
        "pe_gap_pct": pe_model.get("pe_gap_pct"),
        "fair_pb": base_pb,
        "required_fcf_yield_pct": base_fcf_req,
        "hurdle_rate": pe_model.get("hurdle_rate"),
        "primary_method": "Current P/E vs dynamic fair P/E, cross-checked by P/B and FCF yield",
        "fair_pe_drivers": pe_model.get("drivers") or [],
        "fair_pe_scorecard": pe_model.get("scorecard") or [],
        "components": base_components,
        "sensitivity": sensitivity,
        "note": "Model estimate from Yahoo Finance metrics. Fair P/E is dynamic and adjusted by growth, ROE, cash flow, leverage, beta, drawdown, and local hurdle rate; not a broker target price or investment advice.",
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
    conv_note = metrics.get("_conversion_note") or ""
    converted = set(metrics.get("_converted_fields") or [])
    def note(field: str) -> str:
        return conv_note if field in converted else ""
    one_month_period = "30D price return" if mode == "crypto" else "22 trading sessions"
    vol_period = "daily realized, 6M window" if mode == "crypto" else "daily realized, ~6M window"
    risk = metrics.get("_risk_stats") or {}
    ctx = metrics.get("_risk_context") or {}
    metric_rows = [
        _metric("Current Price", _fmt_metric_value(metrics.get("current_price"), "number"), "number", currency, "latest quote"),
        _metric("P/E", _fmt_metric_value(metrics.get("pe"), "ratio"), "ratio", period="TTM"),
        _metric("Fwd P/E", _fmt_metric_value(metrics.get("forward_pe"), "ratio"), "ratio", period="forward 12M estimate"),
        _metric("EV/EBITDA", _fmt_metric_value(metrics.get("ev_ebitda"), "ratio"), "ratio", period="TTM"),
        _metric("P/B", _fmt_metric_value(metrics.get("pb"), "ratio"), "ratio", period="latest book value"),
        _metric("Book Value", _fmt_metric_value(metrics.get("book_value"), "number"), "number", currency, "per share, latest quarter" + note("book_value")),
        _metric("Beta", _fmt_metric_value(metrics.get("beta"), "ratio"), "ratio", period="5Y monthly"),
        _metric("EPS", _fmt_metric_value(metrics.get("eps"), "number"), "number", currency, "TTM" + note("eps")),
        _metric("ROE", _fmt_metric_value(metrics.get("roe_pct"), "percent"), "percent", period="TTM"),
        _metric("Debt/Equity", _fmt_metric_value(metrics.get("debt_to_equity"), "percent"), "percent", period="latest quarter"),
        _metric("Revenue Growth", _fmt_metric_value(metrics.get("revenue_growth_pct"), "percent"), "percent", period="YoY quarterly"),
        _metric("EPS Growth", _fmt_metric_value(metrics.get("eps_growth_pct"), "percent"), "percent", period="YoY quarterly"),
        _metric("Dividend Yield", _fmt_metric_value(metrics.get("dividend_yield_pct"), "percent"), "percent", period="forward annual"),
        _metric("Gross Profit", _fmt_metric_value(metrics.get("gross_profit"), "money"), "money", currency, "TTM" + note("gross_profit")),
        _metric("Total Cash", _fmt_metric_value(metrics.get("total_cash"), "money"), "money", currency, "latest quarter" + note("total_cash")),
        _metric("Free Cash Flow", _fmt_metric_value(metrics.get("free_cash_flow"), "money"), "money", currency, "TTM" + note("free_cash_flow")),
        _metric("FCF Yield", _fmt_metric_value(metrics.get("fcf_yield_pct"), "percent"), "percent", period="TTM FCF / market cap"),
        _metric("Market Cap", _fmt_metric_value(metrics.get("market_cap"), "money"), "money", currency, "latest quote"),
        _metric("24h Volume", _fmt_metric_value(metrics.get("volume_24h"), "money"), "money", currency, "24H"),
        _metric("Liquidity", _fmt_metric_value(metrics.get("liquidity_pct"), "percent"), "percent", period="24H volume / market cap"),
        _metric("1M Return", one_month, "percent", period=one_month_period),
        _metric("6M Return", six_month, "percent", period="6M price return"),
        _metric("Volatility", vol, "percent", period=vol_period),
        _metric("Risk-Free Rate", _fmt_metric_value(risk.get("risk_free_rate"), "percent"), "percent",
                period=f"annual benchmark: {risk.get('risk_free_label') or ctx.get('risk_free_label') or 'risk-free'}"),
        _metric("Hurdle Rate", _fmt_metric_value(risk.get("hurdle_rate"), "percent"), "percent",
                period=f"valuation anchor: {risk.get('hurdle_label') or ctx.get('hurdle_label') or 'risk-free'}"),
        _metric("Annualized Return", _fmt_metric_value(risk.get("annual_return_pct"), "percent"), "percent",
                period="geometric, 6M daily window"),
        _metric("Excess Return", _fmt_metric_value(risk.get("annual_excess_return_pct"), "percent"), "percent",
                period=f"annualized minus {risk.get('risk_free_label') or 'risk-free'}"),
        _metric("Annual Volatility", _fmt_metric_value(risk.get("annual_volatility_pct"), "percent"), "percent",
                period="annualized from 6M daily returns"),
        _metric("Downside Volatility", _fmt_metric_value(risk.get("downside_volatility_pct"), "percent"), "percent",
                period="annualized downside vs risk-free"),
        _metric("Sharpe Ratio", _fmt_metric_value(risk.get("sharpe"), "ratio"), "ratio",
                period=f"annualized vs {risk.get('risk_free_label') or 'risk-free'}, 6M daily"),
        _metric("Sortino Ratio", _fmt_metric_value(risk.get("sortino"), "ratio"), "ratio",
                period=f"downside vs {risk.get('risk_free_label') or 'risk-free'}, 6M daily"),
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
        "risk_context": ctx or None,
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


def risk_benchmarks_from_telemetry(telemetry: list | None) -> dict:
    by_sym = {r.get("symbol"): r for r in telemetry or []}
    usdidr = _num((by_sym.get("USDIDR=X") or {}).get("value"))

    def bench(sym: str, label: str) -> dict:
        r = by_sym.get(sym) or {}
        return {
            "rate": _num(r.get("value")),
            "label": r.get("label") or label,
            "symbol": sym,
            "source": r.get("source_name") or ("Yahoo Finance" if sym.startswith("^") else None),
        }

    bi = bench("BI_RATE", "BI Rate")
    id10 = bench("ID10Y", "Indonesia 10Y SBN")
    irx = bench("^IRX", "US 3M T-Bill")
    tnx = bench("^TNX", "US 10Y Yield")
    return {
        "ID": {
            "risk_free_rate": bi["rate"] if bi["rate"] is not None else id10["rate"],
            "risk_free_label": bi["label"] if bi["rate"] is not None else id10["label"],
            "risk_free_symbol": bi["symbol"] if bi["rate"] is not None else id10["symbol"],
            "risk_free_source": bi["source"] if bi["rate"] is not None else id10["source"],
            "hurdle_rate": id10["rate"] if id10["rate"] is not None else bi["rate"],
            "hurdle_label": id10["label"] if id10["rate"] is not None else bi["label"],
            "hurdle_source": id10["source"] if id10["rate"] is not None else bi["source"],
        },
        "US": {
            "risk_free_rate": irx["rate"] if irx["rate"] is not None else tnx["rate"],
            "risk_free_label": irx["label"] if irx["rate"] is not None else tnx["label"],
            "risk_free_symbol": irx["symbol"] if irx["rate"] is not None else tnx["symbol"],
            "risk_free_source": irx["source"] if irx["rate"] is not None else tnx["source"],
            "hurdle_rate": tnx["rate"] if tnx["rate"] is not None else irx["rate"],
            "hurdle_label": tnx["label"] if tnx["rate"] is not None else irx["label"],
            "hurdle_source": tnx["source"] if tnx["rate"] is not None else irx["source"],
        },
        "CR": {
            "risk_free_rate": irx["rate"] if irx["rate"] is not None else tnx["rate"],
            "risk_free_label": irx["label"] if irx["rate"] is not None else tnx["label"],
            "risk_free_symbol": irx["symbol"] if irx["rate"] is not None else tnx["symbol"],
            "risk_free_source": irx["source"] if irx["rate"] is not None else tnx["source"],
            "hurdle_rate": irx["rate"] if irx["rate"] is not None else tnx["rate"],
            "hurdle_label": irx["label"] if irx["rate"] is not None else tnx["label"],
            "hurdle_source": irx["source"] if irx["rate"] is not None else tnx["source"],
        },
        "fx_rates": {"USDIDR": usdidr},
    }


def enrich(rows: list[dict], previous_by_symbol: dict | None = None,
           refresh_hours: int = 24, workers: int = 6,
           risk_benchmarks: dict | None = None) -> None:
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

    normalized_cache = {}
    sector_pes, country_pes = [], {}
    for row in rows:
        if row.get("country") == "CR":
            continue
        sym = row.get("source_symbol")
        metrics = metric_cache.get(sym) or {}
        if not metrics:
            continue
        risk_context = _risk_context(row, "equity", risk_benchmarks)
        normalized = _normalize_currencies(row, metrics, risk_context)
        normalized_cache[sym] = normalized
        pe = _sanitize_ratio(normalized.get("forward_pe") or normalized.get("pe"), 150.0)
        if pe is not None:
            sector_pes.append(pe)
            country_pes.setdefault(row.get("country") or "", []).append(pe)

    sector_peer_pe = _median(sector_pes) if len(sector_pes) >= 3 else None
    country_peer_pe = {k: _median(v) for k, v in country_pes.items() if len(v) >= 3}

    for row in rows:
        mode = "crypto" if row.get("country") == "CR" else "equity"
        risk_context = _risk_context(row, mode, risk_benchmarks)
        metrics = normalized_cache.get(row.get("source_symbol")) or metric_cache.get(row.get("source_symbol")) or {}
        if mode == "equity" and metrics:
            metrics = dict(metrics)
            country = row.get("country") or ""
            peer = country_peer_pe.get(country) or sector_peer_pe
            if peer is not None:
                metrics["_sector_peer_pe"] = peer
                metrics["_sector_peer_pe_scope"] = (
                    f"{country} sector peer median" if country_peer_pe.get(country) is not None
                    else "mixed-market sector peer median"
                )
        if row.get("country") == "CR":
            row["fundamental_score"] = _score_crypto(row, metrics, risk_context)
        else:
            row["fundamental_score"] = _score_equity(row, metrics, risk_context) if metrics else _pack_score(
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
                    "_risk_context": risk_context,
                    "_risk_stats": _risk_stats(row, "equity", risk_context)},
                _spark_return(row.get("spark"), 22), _spark_return(row.get("spark")),
                _spark_volatility(row.get("spark")))
