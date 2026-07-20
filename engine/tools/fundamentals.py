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


SCORE_SCHEMA_VERSION = 12

BANK_KEYWORDS = (
    "bank", "bancorp", "chase", "wells fargo", "syariah", "btpn", "bpd",
    "rakyat", "mandiri", "negara", "central asia", "jago", "mega",
)
BANK_TICKERS = {
    "BBCA", "BBRI", "BMRI", "BBNI", "BRIS", "BTPS", "MEGA", "ARTO",
    "BJTM", "JPM", "BAC", "WFC",
}
ASSET_LIGHT_FINANCIAL_TICKERS = {"V", "MA", "BLK", "SCHW", "GS", "MS", "AXP", "ADMF"}


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


def _has_real_daily_history(row: dict) -> bool:
    """Risk statistics require observed closes, never interpolated checkpoints."""
    quality = (row.get("chart_quality") or {}).get("6M")
    history_quality = str(row.get("price_history_quality") or "")
    return quality == "historical_close" or "historical_close" in history_quality


def _row_volatility(row: dict):
    return _spark_volatility(row.get("spark")) if _has_real_daily_history(row) else None


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
    if not _has_real_daily_history(row):
        return {}
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


def _valid_beta(v):
    beta = _num(v)
    if beta is None or beta < 0.15 or beta > 4.0:
        return None
    return beta


def _add_warning(metrics: dict, msg: str) -> None:
    warnings = metrics.setdefault("_data_warnings", [])
    if msg not in warnings:
        warnings.append(msg)


def _quarantine_metric_anomalies(row: dict, metrics: dict) -> dict:
    """Hide provider fields that are internally impossible before valuation.

    Yahoo fundamentals can mix IDX quote currency and financial reporting units.
    When a field fails basic sanity checks, we remove only that field and keep
    the market-screen score alive.
    """
    current = _num(metrics.get("current_price"))
    market_cap = _num(metrics.get("market_cap")) or _num(row.get("market_cap_value"))
    eps = _num(metrics.get("eps"))
    pe = _sanitize_ratio(metrics.get("pe"), 1_000_000.0)
    row_ticker = str(row.get("ticker") or "").upper()
    row_name = str(row.get("name") or "").lower()
    row_sector = str(row.get("sector_key") or "").lower()
    row_bank_like = row_ticker in BANK_TICKERS or (
        row_sector == "financials" and any(term in row_name for term in BANK_KEYWORDS)
    )

    if current and eps and eps > 0:
        implied_pe = current / eps
        if implied_pe < 0.5:
            metrics["eps"] = None
            metrics["pe"] = None
            _add_warning(metrics, f"EPS quarantined: implied P/E {implied_pe:.2f}x is not credible")
        elif implied_pe > 300:
            metrics["pe"] = None
            _add_warning(metrics, f"P/E quarantined: implied {implied_pe:.2f}x is outside the screening range")
    elif pe is not None and (pe < 0.5 or pe > 300):
        metrics["pe"] = None
        _add_warning(metrics, f"P/E quarantined: {pe:.2f}x is not credible")

    ratio_limits = (
        ("forward_pe", "Forward P/E", 0.0, 200.0),
        ("pb", "P/B", 0.0, 100.0),
        ("ev_ebitda", "EV/EBITDA", 0.0, 200.0),
    )
    for key, label, lower, upper in ratio_limits:
        value = _num(metrics.get(key))
        if value is not None and (value <= lower or value > upper):
            metrics[key] = None
            _add_warning(metrics, f"{label} quarantined: {value:.2f}x is outside the screening range")

    bounded_percentages = (
        ("dividend_yield_pct", "Dividend yield", 0.0, 20.0),
        ("roe_pct", "ROE", -200.0, 200.0),
        ("debt_to_equity", "Debt/equity", -1_000.0, 1_000.0),
    )
    for key, label, lower, upper in bounded_percentages:
        value = _num(metrics.get(key))
        if value is not None and (value < lower or value > upper):
            metrics[key] = None
            _add_warning(metrics, f"{label} quarantined: {value:.2f}% is outside the screening range")

    if market_cap and market_cap > 0 and not (_is_bank_like(metrics) or row_bank_like):
        field_limits = (
            ("gross_profit", "Gross profit", 5.0),
            ("free_cash_flow", "Free cash flow", 2.0),
            ("total_cash", "Total cash", 5.0),
        )
        for key, label, limit in field_limits:
            val = _num(metrics.get(key))
            if val is not None and abs(val) > market_cap * limit:
                metrics[key] = None
                if key == "free_cash_flow":
                    metrics["fcf_yield_pct"] = None
                _add_warning(metrics, f"{label} quarantined: provider value exceeds {limit:g}x market cap")

    fcf_yield = _num(metrics.get("fcf_yield_pct"))
    if fcf_yield is not None and abs(fcf_yield) > 50:
        metrics["fcf_yield_pct"] = None
        metrics["free_cash_flow"] = None
        _add_warning(metrics, f"FCF yield quarantined: {fcf_yield:.2f}% is not credible")
    return metrics


def _sector_key(metrics: dict) -> str:
    return str(metrics.get("_sector_key") or "").lower()


def _country(metrics: dict) -> str:
    return str(metrics.get("_country") or "").upper()


def _ticker(metrics: dict) -> str:
    return str(metrics.get("_ticker") or "").upper()


def _is_bank_like(metrics: dict) -> bool:
    ticker = _ticker(metrics)
    if ticker in ASSET_LIGHT_FINANCIAL_TICKERS:
        return False
    if ticker in BANK_TICKERS:
        return True
    if _sector_key(metrics) != "financials":
        return False
    name = str(metrics.get("_company_name") or "").lower()
    return any(term in name for term in BANK_KEYWORDS)


def _sector_profile(metrics: dict) -> dict:
    key = _sector_key(metrics)
    if _is_bank_like(metrics):
        return {
            "family": "bank",
            "method": "Bank justified P/B from ROE, sustainable growth, and cost of equity; P/E is a cross-check",
            "scorecard_title": "BANK VALUATION SCORECARD",
        }
    if key in {"energy", "renewables"}:
        return {
            "family": "asset_heavy",
            "method": "Current P/E anchored multiple, cross-checked by FCF yield, EV/EBITDA, and balance-sheet risk",
            "scorecard_title": "SECTOR-ADAPTED P/E SCORECARD",
        }
    if key == "property":
        return {
            "family": "asset_heavy",
            "method": "Current P/E anchored multiple, cross-checked by P/B and asset value",
            "scorecard_title": "PROPERTY VALUATION SCORECARD",
        }
    if key in {"technology", "healthcare", "consumer", "entertainment"}:
        return {
            "family": "compounder",
            "method": "Current P/E anchored multiple, adjusted for growth, quality, cash conversion, and risk",
            "scorecard_title": "COMPOUNDER P/E SCORECARD",
        }
    return {
        "family": "general",
        "method": "Current P/E anchored multiple, adjusted for quality, growth, cash flow, leverage, and risk",
        "scorecard_title": "SECTOR-ADAPTED P/E SCORECARD",
    }


def _country_equity_risk_premium(metrics: dict) -> float:
    country = _country(metrics)
    if country == "ID":
        return 5.0
    if country == "US":
        return 4.0
    return 4.5


def _cost_of_equity(metrics: dict) -> float:
    hurdle = _valuation_hurdle(metrics)
    country = _country(metrics)
    floor = 10.0 if country == "ID" else 7.5 if country == "US" else 8.5
    coe = (hurdle or floor) + _country_equity_risk_premium(metrics)
    return round(_clamp(coe, floor, 18.0), 2)


def _sustainable_growth(metrics: dict, coe: float | None = None) -> tuple[float, str]:
    roe = _num(metrics.get("roe_pct"))
    pe = _sanitize_ratio(metrics.get("pe"), 150.0)
    div_yield = _num(metrics.get("dividend_yield_pct"))
    growth = _growth_anchor(metrics)
    country = _country(metrics)
    cap = 7.0 if country == "ID" else 5.0 if country == "US" else 6.0
    source = "growth metrics"
    if roe is not None and roe > 0 and pe and div_yield is not None and div_yield >= 0:
        earnings_yield = 100 / pe if pe else None
        payout = _clamp(div_yield / earnings_yield, 0.10, 0.85) if earnings_yield else 0.45
        growth = roe * (1 - payout)
        source = f"ROE × retention; payout implied by dividend yield and P/E"
    elif growth is None and roe is not None:
        growth = roe * 0.35
        source = "ROE × assumed retention"
    growth = _clamp(growth if growth is not None else 3.0, -3.0, cap)
    if coe is not None:
        growth = min(growth, max(-3.0, coe - 1.5))
    return round(growth, 2), source


def _valuation_value_score(valuation: dict | None) -> float | None:
    if not valuation:
        return None
    upside = _num(valuation.get("upside_pct"))
    if upside is None:
        return None
    # -30% or worse = very expensive, +30% or better = compelling value.
    return round(_clamp((upside + 30) / 60 * 100, 0, 100))


def _valuation_confidence(metrics: dict, components: list[dict], method: str) -> str:
    required = ["current_price"]
    if method == "bank":
        required += ["book_value", "roe_pct"]
    else:
        required += ["eps", "pe"]
    present = sum(1 for k in required if _num(metrics.get(k)) is not None)
    pe = _num(metrics.get("pe"))
    if method != "bank" and pe is not None and pe > 100:
        return "Medium" if components else "Low"
    if present == len(required) and len(components) >= 2:
        return "High"
    if present >= max(2, len(required) - 1) and components:
        return "Medium"
    return "Low"


def _fetch_equity(sym: str) -> dict:
    import yfinance as yf

    info = yf.Ticker(sym).get_info() or {}
    quote_currency = info.get("currency") or ("IDR" if sym.endswith(".JK") else None)
    financial_currency = info.get("financialCurrency") or quote_currency
    market_cap = _num(info.get("marketCap"))
    fcf = _num(info.get("freeCashflow"))
    fcf_yield = round(fcf / market_cap * 100, 2) if fcf and market_cap else None
    current_price = _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice"))
    volume = (_num(info.get("regularMarketVolume")) or _num(info.get("volume"))
              or _num(info.get("regularMarketVolume3Month")))
    avg_volume = (_num(info.get("averageVolume")) or _num(info.get("averageDailyVolume3Month"))
                  or _num(info.get("regularMarketVolume3Month")))
    avg_volume_10d = _num(info.get("averageVolume10days")) or _num(info.get("averageDailyVolume10Day"))
    avg_liquidity_volume = avg_volume_10d or avg_volume
    avg_daily_value_traded = (current_price * avg_liquidity_volume
                              if current_price and avg_liquidity_volume else None)
    dividend_rate = _num(info.get("dividendRate"))
    # yfinance has returned dividendYield in both decimal and percent form across
    # releases. Prefer the unit-safe dividend-rate/price calculation.
    dividend_yield = (round(dividend_rate / current_price * 100, 2)
                      if dividend_rate is not None and current_price else None)
    if dividend_yield is None:
        raw_yield = _num(info.get("dividendYield"))
        dividend_yield = (round(raw_yield * 100, 2) if raw_yield is not None and raw_yield <= 0.20
                          else round(raw_yield, 2) if raw_yield is not None else None)
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
        "dividend_yield_pct": dividend_yield,
        "gross_profit": _num(info.get("grossProfits")),
        "total_cash": _num(info.get("totalCash")),
        "free_cash_flow": fcf,
        "fcf_yield_pct": fcf_yield,
        "market_cap": market_cap,
        "volume": volume,
        "average_volume": avg_volume,
        "average_volume_10d": avg_volume_10d,
        "avg_daily_value_traded": avg_daily_value_traded,
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

    # TradingView is the IDX market-data authority. Yahoo remains the curated
    # fundamentals provider, but quote-sized fields must use one consistent
    # snapshot so price, market cap, and liquidity cannot drift across panels.
    if (row.get("country") == "ID" and row.get("exchange") == "IDX"
            and row.get("source_provider") == "tradingview"):
        tv_market_cap = _num(row.get("market_cap_value"))
        tv_volume = _num(row.get("volume"))
        tv_avg_10d = _num(row.get("avg_volume_10d"))
        tv_avg_30d = _num(row.get("avg_volume_30d"))
        current = _num(metrics.get("current_price"))
        if tv_market_cap is not None:
            metrics["market_cap"] = tv_market_cap
        if tv_volume is not None:
            metrics["volume"] = tv_volume
        if tv_avg_10d is not None:
            metrics["average_volume_10d"] = tv_avg_10d
        if tv_avg_30d is not None:
            metrics["average_volume"] = tv_avg_30d
        avg_volume = tv_avg_10d or tv_avg_30d
        if current is not None and avg_volume is not None:
            metrics["avg_daily_value_traded"] = current * avg_volume
        metrics["quote_source"] = "TradingView"

    factor = _fx_factor(financial_currency, quote_currency, (risk_context or {}).get("fx_rates"))
    needs_conversion = (financial_currency and quote_currency
                        and financial_currency != quote_currency and factor)
    converted_fields = []
    if needs_conversion:
        current = _num(metrics.get("current_price"))
        market_cap = _num(metrics.get("market_cap")) or _num(row.get("market_cap_value"))
        for key in ("gross_profit", "total_cash", "free_cash_flow"):
            val = _num(metrics.get(key))
            if val is not None:
                converted = val * factor
                raw_pct = abs(val / market_cap * 100) if market_cap else None
                converted_pct = abs(converted / market_cap * 100) if market_cap else None
                raw_plausible = raw_pct is not None and 0.005 <= raw_pct <= 300
                converted_plausible = converted_pct is not None and 0.005 <= converted_pct <= 300
                if converted_plausible and not raw_plausible:
                    metrics[key] = converted
                    converted_fields.append(key)
                elif not raw_plausible and not converted_plausible:
                    metrics[key] = None
                else:
                    metrics[key] = val
        for key in ("book_value", "eps"):
            val = _num(metrics.get(key))
            if val is None:
                continue
            converted = val * factor
            raw_ratio = abs(current / val) if current and val else None
            converted_ratio = abs(current / converted) if current and converted else None
            provider_ratio = _sanitize_ratio(metrics.get("pe" if key == "eps" else "pb"), 1_000_000.0)

            def close_to_provider(ratio) -> bool:
                if ratio is None or provider_ratio is None or provider_ratio <= 0:
                    return False
                return abs(ratio / provider_ratio - 1) <= 0.25

            if key == "eps":
                # Yahoo often marks IDX financials as USD while trailing EPS is
                # already aligned with the IDR share price. If raw EPS recreates
                # Yahoo's own P/E, never convert it again.
                if close_to_provider(raw_ratio) or (raw_ratio is not None and 0.5 <= raw_ratio <= 500):
                    metrics[key] = val
                elif close_to_provider(converted_ratio) or (converted_ratio is not None and 0.5 <= converted_ratio <= 500):
                    metrics[key] = converted
                    converted_fields.append(key)
                else:
                    metrics[key] = None
            else:
                raw_plausible = raw_ratio is not None and 0.05 <= raw_ratio <= 100
                converted_plausible = converted_ratio is not None and 0.05 <= converted_ratio <= 100
                if converted_plausible and not raw_plausible:
                    metrics[key] = converted
                    converted_fields.append(key)
                elif raw_plausible and not converted_plausible:
                    metrics[key] = val
                elif close_to_provider(converted_ratio):
                    metrics[key] = converted
                    converted_fields.append(key)
                elif close_to_provider(raw_ratio):
                    metrics[key] = val
                else:
                    metrics[key] = converted if converted_plausible else val
                    if converted_plausible:
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
    metrics["ev_ebitda"] = _num(metrics.get("ev_ebitda"))
    metrics["fcf_yield_pct"] = round(fcf / market_cap * 100, 2) if fcf and market_cap else metrics.get("fcf_yield_pct")
    metrics = _quarantine_metric_anomalies(row, metrics)
    return metrics


def _equity_liquidity(row: dict, metrics: dict) -> dict:
    current = _num(metrics.get("current_price")) or _num(row.get("value"))
    market_cap = _num(metrics.get("market_cap")) or _num(row.get("market_cap_value"))
    volume = _num(metrics.get("volume")) or _num(row.get("volume"))
    avg_volume = (_num(metrics.get("average_volume_10d"))
                  or _num(metrics.get("average_volume")))
    traded_value = _num(row.get("turnover")) or (current * volume if current and volume else None)
    avg_daily_value = (_num(metrics.get("avg_daily_value_traded"))
                       or (current * avg_volume if current and avg_volume else None))
    liquidity_value = avg_daily_value or traded_value
    liquidity_pct = (liquidity_value / market_cap * 100) if liquidity_value and market_cap else None
    currency = (metrics.get("quote_currency") or metrics.get("currency") or "").upper()
    country = row.get("country")
    absolute_value = liquidity_value or traded_value

    pct_score = _score_high(liquidity_pct, 0.02, 0.35)
    if country == "ID" or currency == "IDR":
        abs_score = _score_high(absolute_value, 1_000_000_000, 25_000_000_000)
    else:
        abs_score = _score_high(absolute_value, 2_000_000, 50_000_000)

    return {
        "volume": volume,
        "average_volume": _num(metrics.get("average_volume")),
        "average_volume_10d": _num(metrics.get("average_volume_10d")),
        "traded_value": traded_value,
        "avg_daily_value_traded": avg_daily_value,
        "liquidity_pct": round(liquidity_pct, 2) if liquidity_pct is not None else None,
        "liquidity_score": _avg([pct_score, abs_score]),
    }


def _score_equity(row: dict, metrics: dict, risk_context: dict | None = None) -> dict:
    metrics = _normalize_currencies(row, metrics, risk_context)
    metrics["_ticker"] = row.get("ticker")
    metrics["_company_name"] = row.get("name")
    metrics["_sector_key"] = row.get("sector_key")
    metrics["_sector_name"] = row.get("sector_name")
    metrics["_country"] = row.get("country")
    metrics["_exchange"] = row.get("exchange")
    metrics["_risk_context"] = risk_context or {}
    metrics["_risk_stats"] = _risk_stats(row, "equity", risk_context)
    one_month = _spark_return(row.get("spark"), 22)
    six_month = _spark_return(row.get("spark"))
    vol = _row_volatility(row)
    valuation = _valuation(metrics)
    metrics["_valuation_cached"] = valuation
    valuation_score = _valuation_value_score(valuation)
    profile = _sector_profile(metrics)
    liquidity = _equity_liquidity(row, metrics)
    metrics.update({k: v for k, v in liquidity.items() if v is not None})

    if profile["family"] == "bank":
        value = _avg([
            valuation_score,
            valuation_score,
            _score_low(metrics.get("pb"), 1.2, 4.5),
            _score_low(metrics.get("forward_pe") or metrics.get("pe"), 8, 24),
            _score_high(metrics.get("dividend_yield_pct"), 0, 5),
        ])
        quality = _avg([
            _score_high(metrics.get("roe_pct"), 8, 22),
            _score_high(metrics.get("eps_growth_pct"), -8, 18),
            _score_high(metrics.get("dividend_yield_pct"), 0, 5),
        ])
        risk = _avg([
            _score_low(vol, 1.2, 5.0),
            _score_high(six_month, -35, 15),
        ])
    else:
        value = _avg([
            valuation_score,
            valuation_score,
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
        risk = _avg([
            _score_low(vol, 1.2, 5.0),
            _score_low(metrics.get("debt_to_equity"), 40, 250),
            _score_high(six_month, -35, 15),
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
    axes = [
        {"key": "value", "label": "Value", "score": value},
        {"key": "quality", "label": "Quality", "score": quality},
        {"key": "growth", "label": "Growth", "score": growth},
        {"key": "momentum", "label": "Momentum", "score": momentum},
        {"key": "liquidity", "label": "Liquidity", "score": metrics.get("liquidity_score")},
        {"key": "risk", "label": "Risk", "score": risk},
    ]
    return _pack_score("equity", axes, metrics, one_month, six_month, vol)


def _score_crypto(row: dict, metrics: dict, risk_context: dict | None = None) -> dict:
    metrics = dict(metrics)
    metrics["current_price"] = _num(row.get("value")) or _num(metrics.get("current_price"))
    metrics["_risk_context"] = risk_context or {}
    metrics["_risk_stats"] = _risk_stats(row, "crypto", risk_context)
    one_month = _spark_return(row.get("spark"), 30)
    six_month = _spark_return(row.get("spark"))
    vol = _row_volatility(row)
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


def _score_mid(v, ideal: float, lo: float, hi: float):
    v = _num(v)
    if v is None:
        return None
    if v == ideal:
        return 100
    if v < ideal:
        if v <= lo:
            return 0
        return round((v - lo) / (ideal - lo) * 100)
    if v >= hi:
        return 0
    return round(100 - ((v - ideal) / (hi - ideal) * 100))


def _score_idx_screen(row: dict, risk_context: dict | None = None) -> dict:
    """Screen-grade score for full-IDX TradingView rows.

    This intentionally avoids valuation/fundamental claims. It is a tradability
    and market-quality screen built from TradingView scanner fields available for
    the whole IDX universe.
    """
    current = _num(row.get("value"))
    market_cap = _num(row.get("market_cap_value"))
    volume = _num(row.get("volume"))
    avg_volume = _num(row.get("avg_volume_10d")) or _num(row.get("avg_volume_30d"))
    traded_value = _num(row.get("turnover")) or (current * volume if current and volume else None)
    avg_daily_value = current * avg_volume if current and avg_volume else None
    liquidity_value = avg_daily_value or traded_value
    liquidity_pct = (liquidity_value / market_cap * 100) if liquidity_value and market_cap else None
    rel_vol = _num(row.get("relative_volume_10d"))
    rec = _num(row.get("recommend_all"))
    rsi = _num(row.get("rsi"))
    perf_1w = _num(row.get("perf_1w"))
    perf_1m = _num(row.get("perf_1m"))
    perf_3m = _num(row.get("perf_3m"))
    perf_6m = _num(row.get("perf_6m"))
    vol_1m = _num(row.get("volatility_1m"))
    vol_1w = _num(row.get("volatility_1w"))
    ctx = _risk_context(row, "equity", risk_context)
    metrics = {
        "currency": "IDR",
        "quote_currency": "IDR",
        "current_price": current,
        "market_cap": market_cap,
        "volume": volume,
        "average_volume_10d": _num(row.get("avg_volume_10d")),
        "average_volume": _num(row.get("avg_volume_30d")),
        "traded_value": traded_value,
        "avg_daily_value_traded": avg_daily_value,
        "liquidity_pct": round(liquidity_pct, 2) if liquidity_pct is not None else None,
        "relative_volume_10d": rel_vol,
        "recommend_all": rec,
        "rsi": rsi,
        "analyst_target_low": _num(row.get("analyst_target_low")),
        "analyst_target_median": _num(row.get("analyst_target_median")),
        "analyst_target_high": _num(row.get("analyst_target_high")),
        "perf_1w": perf_1w,
        "perf_3m": perf_3m,
        "volatility_1m": vol_1m,
        "source": "TradingView IDX screen",
        "as_of": _now_iso(),
        "_risk_context": ctx,
        "_risk_stats": _risk_stats(row, "equity", ctx),
    }
    liquidity_axis = _avg([
        _score_high(liquidity_value, 1_000_000_000, 25_000_000_000),
        _score_high(liquidity_pct, 0.02, 0.35),
    ])
    axes = [
        {"key": "size", "label": "Size", "score": _score_high(market_cap, 500_000_000_000, 100_000_000_000_000)},
        {"key": "liquidity", "label": "Liquidity", "score": liquidity_axis},
        {"key": "momentum", "label": "Momentum", "score": _avg([
            _score_high(row.get("delta_pct"), -3, 3),
            _score_high(perf_1m, -10, 15),
            _score_high(perf_6m, -35, 35),
        ])},
        {"key": "technical", "label": "Technical", "score": _avg([
            _score_mid(rsi, 55, 25, 85),
            _score_high(rec, -0.6, 0.6),
        ])},
        {"key": "activity", "label": "Activity", "score": _avg([
            _score_mid(rel_vol, 1.15, 0.25, 3.0),
            _score_high(traded_value, 500_000_000, 20_000_000_000),
        ])},
        {"key": "risk", "label": "Risk", "score": _avg([
            _score_low(vol_1m or vol_1w, 2.0, 12.0),
            _score_high(perf_3m, -25, 20),
            _score_high(perf_6m, -45, 25),
        ])},
    ]
    score = _pack_score("idx_screen", axes, metrics, perf_1m, perf_6m, vol_1m or vol_1w)
    target_low = _num(metrics.get("analyst_target_low"))
    target = _num(metrics.get("analyst_target_median"))
    target_high = _num(metrics.get("analyst_target_high"))
    valid_target = (
        current is not None and current > 0 and target is not None and target > 0
        and (target_low is None or target_low > 0)
        and (target_high is None or target_high > 0)
        and (target_low is None or target_low <= target)
        and (target_high is None or target <= target_high)
        and 0.1 <= target / current <= 10
    )
    if valid_target:
        upside = round((target / current - 1) * 100, 2)
        score["valuation"] = {
            "valuation_model": "tradingview_analyst_consensus",
            "valuation_confidence": "Reference",
            "currency": "IDR",
            "current_price": current,
            "target_price": round(target, 2),
            "target_low": round(target_low, 2) if target_low is not None else None,
            "target_high": round(target_high, 2) if target_high is not None else None,
            "upside_pct": upside,
            "status": "Analyst consensus",
            "signal": "Consensus upside" if upside > 10 else "Consensus downside" if upside < -10 else "Near consensus",
            "source": "TradingView analyst consensus",
        }
    score["screen_grade"] = True
    score["source"] = "TradingView IDX screen"
    score["note"] = (
        "Screen-grade IDX score from TradingView price, market cap, liquidity, "
        "performance, volatility, RSI, and technical recommendation. It is not "
        "a fundamental valuation score."
    )
    return score


def _score_idx_fallback(row: dict, risk_context: dict | None = None) -> dict:
    """Low-confidence score for curated IDX names absent from TradingView scanner."""
    current = _num(row.get("value"))
    volume = _num(row.get("volume"))
    turnover = _num(row.get("turnover")) or (current * volume if current and volume else None)
    ctx = _risk_context(row, "equity", risk_context)
    metrics = {
        "currency": "IDR",
        "quote_currency": "IDR",
        "current_price": current,
        "volume": volume,
        "traded_value": turnover,
        "source": "Yahoo fallback: absent from TradingView IDX scanner",
        "as_of": _now_iso(),
        "_risk_context": ctx,
        "_risk_stats": _risk_stats(row, "equity", ctx),
    }
    axes = [
        {"key": "size", "label": "Size", "score": None},
        {"key": "liquidity", "label": "Liquidity", "score": _score_high(turnover, 500_000_000, 20_000_000_000)},
        {"key": "momentum", "label": "Momentum", "score": _avg([
            _score_high(row.get("delta_pct"), -3, 3),
            _score_high(_spark_return(row.get("spark"), 22), -8, 12),
            _score_high(_spark_return(row.get("spark")), -20, 35),
        ])},
        {"key": "technical", "label": "Technical", "score": None},
        {"key": "activity", "label": "Activity", "score": 0 if volume == 0 else _score_high(volume, 100_000, 10_000_000)},
        {"key": "risk", "label": "Risk", "score": _score_low(_row_volatility(row), 1.2, 5.0)},
    ]
    score = _pack_score("idx_screen", axes, metrics, _spark_return(row.get("spark"), 22),
                        _spark_return(row.get("spark")), _row_volatility(row))
    score["screen_grade"] = True
    score["source"] = "Yahoo fallback: absent from TradingView IDX scanner"
    score["note"] = (
        "Low-confidence fallback for a curated IDX ticker that TradingView's IDX "
        "scanner did not return. Treat as stale or inactive until provider "
        "coverage returns."
    )
    return score


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
    """Fair P/E bridge anchored to the stock's own traded multiple.

    Sector P/E is deliberately a sanity check, not the primary anchor. That
    keeps high-quality compounders from being dragged to a weak peer median and
    keeps optically cheap names from receiving a free rerating.
    """
    current_pe = _sanitize_ratio(metrics.get("pe"), 500.0)
    forward_pe = _sanitize_ratio(metrics.get("forward_pe"), 500.0)
    sector_pe = _sanitize_ratio(metrics.get("_sector_peer_pe"), 150.0)
    sector_scope = metrics.get("_sector_peer_pe_scope") or "sector peer median"
    roe = _num(metrics.get("roe_pct"))
    debt = _num(metrics.get("debt_to_equity"))
    fcf_yield = _num(metrics.get("fcf_yield_pct"))
    beta = _valid_beta(metrics.get("beta"))
    growth = _growth_anchor(metrics)
    hurdle = _valuation_hurdle(metrics)
    profile = _sector_profile(metrics)

    hurdle_base = _clamp(100 / ((hurdle or 5.0) + 2.0), 8.0, 18.0)
    if current_pe is not None:
        base = current_pe
        base_label = "Current P/E Anchor"
        base_note = "actual traded trailing P/E"
    elif forward_pe is not None:
        base = forward_pe
        base_label = "Forward P/E Anchor"
        base_note = "actual traded forward P/E"
    elif sector_pe is not None:
        base = _clamp(sector_pe, 6.0, 35.0)
        base_label = "Peer Fallback P/E"
        base_note = sector_scope
    else:
        base = hurdle_base
        base_label = "Hurdle Fallback P/E"
        base_note = f"hurdle {hurdle:.2f}%" if hurdle is not None else "fallback rate anchor"

    adjustments: list[float] = []
    drivers: list[str] = []
    scorecard: list[dict] = [{
        "label": base_label,
        "metric": base_note,
        "value": round(base, 2),
        "fmt": "multiple",
        "adjustment": None,
    }]

    if sector_pe is not None:
        gap = round((current_pe / sector_pe - 1) * 100, 1) if current_pe and sector_pe else None
        scorecard.append({
            "label": "Sector P/E Sanity Check",
            "metric": f"{sector_scope}{f'; current vs peer {gap:+.1f}%' if gap is not None else ''}",
            "value": round(sector_pe, 2),
            "fmt": "multiple",
            "adjustment": None,
            "note": "reference only; not the primary valuation anchor",
        })

    def add_adjustment(label: str, metric: str, adj: float, note: str) -> None:
        adjustments.append(adj)
        scorecard.append({
            "label": label,
            "metric": metric,
            "adjustment": round(adj, 2),
            "fmt": "multiple",
            "note": note,
        })

    if roe is not None:
        adj = _clamp(base * ((roe - 12) / 100), -base * 0.15, base * 0.25)
        add_adjustment("Quality Adjustment", f"ROE {roe:.1f}%", adj,
                       "higher ROE deserves a premium to the stock's current multiple")
        drivers.append(f"ROE {roe:.1f}% {'adds' if adj >= 0 else 'subtracts'} {abs(adj):.1f}x from fair P/E")

    if growth is not None:
        adj = _clamp(base * ((growth - 5) / 80), -base * 0.20, base * 0.30)
        add_adjustment("Growth Adjustment", f"revenue/EPS growth {growth:.1f}%", adj,
                       "growth above 5% earns a premium; weak growth earns a discount")
        drivers.append(f"growth {growth:.1f}% {'adds' if adj >= 0 else 'subtracts'} {abs(adj):.1f}x")

    if fcf_yield is not None:
        req = _required_fcf_yield(metrics)
        if fcf_yield >= req:
            adj = base * 0.10
        elif fcf_yield >= req * 0.5:
            adj = base * 0.03
        elif fcf_yield <= 0:
            adj = -base * 0.18
        else:
            adj = -base * 0.08
        add_adjustment("Cash-Flow Adjustment", f"FCF yield {fcf_yield:.1f}% vs required {req:.1f}%", adj,
                       "cash yield checks whether earnings convert into owner cash")
        drivers.append(f"FCF yield {fcf_yield:.1f}% {'supports' if adj >= 0 else 'pressures'} valuation")

    if debt is not None and profile["family"] != "bank":
        if debt <= 40:
            adj = base * 0.05
        elif debt <= 120:
            adj = 0.0
        else:
            adj = -_clamp(base * ((debt - 120) / 500), base * 0.05, base * 0.18)
        add_adjustment("Balance-Sheet Adjustment", f"Debt/Equity {debt:.1f}%", adj,
                       "excess leverage limits rerating potential")
        drivers.append(f"Debt/Equity {debt:.1f}% {'supports' if adj >= 0 else 'cuts'} the multiple")

    if beta is not None:
        if beta <= 0.8:
            adj = base * 0.05
        elif beta <= 1.2:
            adj = 0.0
        else:
            adj = -_clamp(base * ((beta - 1.2) / 8), base * 0.03, base * 0.15)
        add_adjustment("Market-Risk Adjustment", f"Beta {beta:.2f}x", adj,
                       "higher market beta deserves a modest discount")
        drivers.append(f"beta {beta:.2f}x {'supports' if adj >= 0 else 'cuts'} fair P/E")
    elif metrics.get("beta") is not None:
        scorecard.append({
            "label": "Market-Risk Adjustment",
            "metric": f"Beta {metrics.get('beta')} ignored as unreliable",
            "adjustment": 0,
            "fmt": "multiple",
            "note": "near-zero or extreme beta is not used for valuation",
        })

    if forward_pe is not None and current_pe is not None:
        if forward_pe < current_pe * 0.9 and (growth or 0) > 0:
            adj = base * 0.05
            add_adjustment("Forward-Earnings Adjustment", f"Fwd P/E {forward_pe:.1f}x vs current {current_pe:.1f}x", adj,
                           "forward earnings imply valuation support")
            drivers.append(f"forward P/E {forward_pe:.1f}x is below current {current_pe:.1f}x")
        elif forward_pe > current_pe * 1.15:
            adj = -base * 0.05
            add_adjustment("Forward-Earnings Adjustment", f"Fwd P/E {forward_pe:.1f}x vs current {current_pe:.1f}x", adj,
                           "forward earnings imply valuation risk")
            drivers.append(f"forward P/E {forward_pe:.1f}x is above current {current_pe:.1f}x")

    if sector_pe is not None and current_pe is not None:
        if current_pe > sector_pe * 1.75 and (growth or 0) < 8 and (roe or 0) < 18:
            adj = -base * 0.08
            add_adjustment("Peer Sanity Adjustment", f"current P/E {current_pe:.1f}x vs peer {sector_pe:.1f}x", adj,
                           "small discount because premium is not backed by growth or ROE")
            drivers.append("peer sanity check trims unsupported premium")
        elif current_pe < sector_pe * 0.65 and ((growth or 0) >= 5 or (roe or 0) >= 15):
            adj = base * 0.05
            add_adjustment("Peer Sanity Adjustment", f"current P/E {current_pe:.1f}x vs peer {sector_pe:.1f}x", adj,
                           "small premium because quality/growth is not reflected in current multiple")
            drivers.append("peer sanity check supports a modest rerating")

    pre_cap_fair_pe = base + sum(adjustments)
    fair_pe = pre_cap_fair_pe
    cap_note = None
    if current_pe is not None:
        if (growth or 0) >= 20 and (roe or 0) >= 12:
            premium_cap = 1.65
        elif (growth or 0) >= 8 or (roe or 0) >= 18:
            premium_cap = 1.50
        else:
            premium_cap = 1.35
        lower = max(4.0, current_pe * 0.65)
        upper = min(500.0, current_pe * premium_cap)
        fair_pe = _clamp(fair_pe, lower, max(lower, upper))
        if round(fair_pe, 2) != round(pre_cap_fair_pe, 2):
            cap_note = f"bounded to {lower:.1f}x-{upper:.1f}x around current P/E {current_pe:.1f}x"
    else:
        fair_pe = _clamp(fair_pe, 5.0, 35.0)
        if round(fair_pe, 2) != round(pre_cap_fair_pe, 2):
            cap_note = "bounded to 5.0x-35.0x because current P/E is unavailable"

    if cap_note:
        scorecard.append({
            "label": "Current-Multiple Guardrail",
            "metric": cap_note,
            "adjustment": round(fair_pe - pre_cap_fair_pe, 2),
            "fmt": "multiple",
            "note": "prevents unsupported rerating or derating",
        })
    scorecard.append({
        "label": "Final Fair P/E",
        "metric": "current multiple + explicit premiums/discounts",
        "value": round(fair_pe, 2),
        "fmt": "multiple",
        "adjustment": None,
    })

    pe_gap = round((fair_pe / current_pe - 1) * 100, 2) if current_pe else None
    return {
        "fair_pe": round(fair_pe, 2),
        "current_pe": round(current_pe, 2) if current_pe is not None else None,
        "forward_pe": round(forward_pe, 2) if forward_pe is not None else None,
        "sector_peer_pe": round(sector_pe, 2) if sector_pe is not None else None,
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
    if current and current > 0 and fcf_yield and 0 < fcf_yield <= 50 and required_fcf_yield > 0:
        candidates.append({
            "method": f"Current price × FCF yield / {required_fcf_yield:g}%",
            "price": current * (fcf_yield / required_fcf_yield),
            "input": f"FCF yield {round(fcf_yield, 2)}%",
        })
    return candidates


def _bank_valuation_components(metrics: dict, fair_pb: float, fair_pe: float | None) -> list[dict]:
    candidates = []
    book = _num(metrics.get("book_value"))
    current = _num(metrics.get("current_price"))
    eps = _num(metrics.get("eps"))
    forward_pe = _sanitize_ratio(metrics.get("forward_pe"), 150.0)
    if book and book > 0:
        candidates.append({
            "method": f"Book value × {fair_pb:g} justified P/B",
            "price": book * fair_pb,
            "input": f"Book value {round(book, 2)}, ROE {round(_num(metrics.get('roe_pct')) or 0, 2)}%",
        })
    if eps and eps > 0 and fair_pe:
        candidates.append({
            "method": f"EPS × {fair_pe:g} fair P/E cross-check",
            "price": eps * fair_pe,
            "input": f"EPS {round(eps, 2)}, current P/E {round(_sanitize_ratio(metrics.get('pe'), 150.0) or 0, 2)}x",
        })
    if current and current > 0 and forward_pe and fair_pe:
        forward_eps = current / forward_pe
        candidates.append({
            "method": f"Forward EPS × {fair_pe:g} fair P/E cross-check",
            "price": forward_eps * fair_pe,
            "input": f"implied forward EPS {round(forward_eps, 2)}, forward P/E {round(forward_pe, 2)}x",
        })
    return candidates


def _bank_valuation(metrics: dict) -> dict | None:
    current = _num(metrics.get("current_price"))
    book = _num(metrics.get("book_value"))
    roe = _num(metrics.get("roe_pct"))
    if not current or current <= 0 or not book or book <= 0 or roe is None:
        return None

    current_pb = _sanitize_ratio(metrics.get("pb"), 80.0)
    current_pe = _sanitize_ratio(metrics.get("pe"), 150.0)
    forward_pe = _sanitize_ratio(metrics.get("forward_pe"), 150.0)
    sector_pe = _sanitize_ratio(metrics.get("_sector_peer_pe"), 150.0)
    sector_scope = metrics.get("_sector_peer_pe_scope") or "sector peer median"
    coe = _cost_of_equity(metrics)
    growth, growth_source = _sustainable_growth(metrics, coe)
    roe_dec = roe / 100
    coe_dec = coe / 100
    growth_dec = growth / 100
    denom = coe_dec - growth_dec
    if denom <= 0.005 or roe_dec <= 0:
        return None

    justified_pb = _clamp((roe_dec - growth_dec) / denom, 0.4, 6.0)
    fair_pb = justified_pb
    guardrail_note = None
    if current_pb:
        lower = max(0.4, current_pb * 0.65)
        upper = min(6.0, current_pb * 1.50)
        fair_pb = _clamp(justified_pb, lower, max(lower, upper))
        if round(fair_pb, 2) != round(justified_pb, 2):
            guardrail_note = f"bounded to {lower:.2f}x-{upper:.2f}x around current P/B {current_pb:.2f}x"

    fair_pe = fair_pb / roe_dec if roe_dec > 0 else None
    if fair_pe and current_pe:
        fair_pe = _clamp(fair_pe, max(4.0, current_pe * 0.65), min(45.0, current_pe * 1.55))
    elif fair_pe:
        fair_pe = _clamp(fair_pe, 4.0, 35.0)

    scorecard = [
        {"label": "Current P/B Anchor", "metric": "actual traded P/B", "value": round(current_pb, 2) if current_pb else None, "fmt": "multiple", "adjustment": None},
        {"label": "Current P/E Cross-Check", "metric": "actual traded trailing P/E", "value": round(current_pe, 2) if current_pe else None, "fmt": "multiple", "adjustment": None},
        {"label": "Cost of Equity", "metric": "local hurdle rate + country equity risk premium", "value": coe, "fmt": "percent", "adjustment": None},
        {"label": "Sustainable Growth", "metric": growth_source, "value": growth, "fmt": "percent", "adjustment": None},
        {"label": "Justified P/B", "metric": "(ROE - growth) / (cost of equity - growth)", "value": round(justified_pb, 2), "fmt": "multiple", "adjustment": None},
    ]
    if guardrail_note:
        scorecard.append({
            "label": "Current-Multiple Guardrail",
            "metric": guardrail_note,
            "value": round(fair_pb, 2),
            "fmt": "multiple",
            "adjustment": None,
            "note": "keeps the screen from projecting an unsupported valuation cliff",
        })
    scorecard.extend([
        {"label": "Final Fair P/B", "metric": "justified P/B with current-multiple guardrail", "value": round(fair_pb, 2), "fmt": "multiple", "adjustment": None},
        {"label": "Fair P/E Cross-Check", "metric": "fair P/B divided by ROE", "value": round(fair_pe, 2) if fair_pe else None, "fmt": "multiple", "adjustment": None},
    ])
    if sector_pe is not None:
        scorecard.append({
            "label": "Sector P/E Sanity Check",
            "metric": f"{sector_scope}; reference only",
            "value": round(sector_pe, 2),
            "fmt": "multiple",
            "adjustment": None,
        })

    scenarios = [
        ("Bear", round(max(0.4, fair_pb * 0.82), 2), round(fair_pe * 0.88, 2) if fair_pe else None),
        ("Base", round(fair_pb, 2), round(fair_pe, 2) if fair_pe else None),
        ("Bull", round(min(7.0, fair_pb * 1.18), 2), round(fair_pe * 1.12, 2) if fair_pe else None),
    ]
    sensitivity, base_components = [], []
    for name, pb_mult, pe_mult in scenarios:
        components = _bank_valuation_components(metrics, pb_mult, pe_mult)
        target = _median([c["price"] for c in components])
        if target:
            sensitivity.append({
                "case": name,
                "target": round(target, 2),
                "upside_pct": round((target / current - 1) * 100, 2),
                "assumptions": f"justified P/B {pb_mult:g}x, fair P/E {pe_mult:g}x" if pe_mult else f"justified P/B {pb_mult:g}x",
                "components": components,
            })
        if name == "Base":
            base_components = components

    fair = next((s["target"] for s in sensitivity if s["case"] == "Base"), None)
    if not fair:
        return None

    return _valuation_payload(
        metrics=metrics,
        fair=fair,
        current=current,
        sensitivity=sensitivity,
        base_components=base_components,
        valuation_model="bank_justified_pb",
        primary_method=_sector_profile(metrics)["method"],
        scorecard=scorecard,
        scorecard_title="BANK VALUATION SCORECARD",
        current_pe=current_pe,
        forward_pe=forward_pe,
        fair_pe=fair_pe,
        base_pe=current_pe,
        base_pe_source="actual traded P/E; bank value anchored to justified P/B",
        fair_pb=fair_pb,
        required_fcf_yield_pct=None,
        hurdle_rate=coe,
        confidence=_valuation_confidence(metrics, base_components, "bank"),
        drivers=[
            f"ROE {roe:.1f}% and sustainable growth {growth:.1f}% imply justified P/B {justified_pb:.2f}x",
            f"cost of equity {coe:.1f}% is the bank valuation hurdle",
            f"current P/B {current_pb:.2f}x is used as a sanity guardrail" if current_pb else "current P/B unavailable; no traded multiple guardrail",
        ],
        note=(
            "Bank method: fair value is driven by justified P/B from ROE, sustainable growth, and cost of equity. "
            "P/E and sector P/E are shown as cross-checks only; this is a screening estimate, not a broker target or investment advice."
        ),
    )


def _valuation_payload(metrics: dict, fair: float, current: float, sensitivity: list[dict],
                       base_components: list[dict], valuation_model: str,
                       primary_method: str, scorecard: list[dict],
                       scorecard_title: str, current_pe=None, forward_pe=None,
                       fair_pe=None, base_pe=None, base_pe_source=None,
                       fair_pb=None, required_fcf_yield_pct=None, hurdle_rate=None,
                       confidence: str = "Medium", drivers: list[str] | None = None,
                       note: str = "") -> dict:
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
    pe_gap = round((fair_pe / current_pe - 1) * 100, 2) if fair_pe and current_pe else None
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
        "valuation_model": valuation_model,
        "valuation_confidence": confidence,
        "current_pe": round(current_pe, 2) if current_pe is not None else None,
        "forward_pe": round(forward_pe, 2) if forward_pe is not None else None,
        "base_pe": round(base_pe, 2) if base_pe is not None else None,
        "base_pe_source": base_pe_source,
        "fair_pe": round(fair_pe, 2) if fair_pe is not None else None,
        "pre_guardrail_fair_pe": None,
        "pe_gap_pct": pe_gap,
        "fair_pb": round(fair_pb, 2) if fair_pb is not None else None,
        "required_fcf_yield_pct": required_fcf_yield_pct,
        "hurdle_rate": round(hurdle_rate, 2) if hurdle_rate is not None else None,
        "primary_method": primary_method,
        "scorecard_title": scorecard_title,
        "fair_pe_drivers": (drivers or [])[:6],
        "fair_pe_scorecard": [r for r in scorecard if r.get("value") is not None or r.get("adjustment") is not None],
        "components": base_components,
        "sensitivity": sensitivity,
        "note": note,
    }


def _valuation(metrics: dict) -> dict | None:
    """Multiple-based fair-value estimate from provider fields.

    This is intentionally conservative and transparent: it uses only inputs Yahoo
    already supplied, then reports the method and components so the UI can avoid
    treating it as a broker target price.
    """
    current = _num(metrics.get("current_price"))
    if not current or current <= 0:
        return None

    if _is_bank_like(metrics):
        bank = _bank_valuation(metrics)
        if bank:
            return bank

    # A peer or hurdle multiple is useful context, but it is not defensible as
    # the primary target-price anchor. Without an observed current/forward P/E,
    # keep the screen score and hide valuation.
    if (_sanitize_ratio(metrics.get("pe"), 500.0) is None
            and _sanitize_ratio(metrics.get("forward_pe"), 500.0) is None):
        return None

    pe_model = _fair_pe_model(metrics)
    base_pe = pe_model["fair_pe"]
    base_pb = _fair_pb(metrics)
    base_fcf_req = _required_fcf_yield(metrics)
    profile = _sector_profile(metrics)
    scenarios = [
        ("Bear", round(max(5.0, base_pe * 0.8), 2), round(max(0.7, base_pb * 0.75), 2), round(min(15.0, base_fcf_req * 1.25), 2)),
        ("Base", base_pe, base_pb, base_fcf_req),
        ("Bull", round(min(500.0, base_pe * 1.25), 2), round(min(5.0, base_pb * 1.25), 2), round(max(4.0, base_fcf_req * 0.8), 2)),
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

    return _valuation_payload(
        metrics=metrics,
        fair=fair,
        current=current,
        sensitivity=sensitivity,
        base_components=base_components,
        valuation_model=f"{profile['family']}_current_pe_anchor",
        primary_method=profile["method"],
        scorecard=pe_model.get("scorecard") or [],
        scorecard_title=profile["scorecard_title"],
        current_pe=pe_model.get("current_pe"),
        forward_pe=pe_model.get("forward_pe"),
        fair_pe=pe_model.get("fair_pe"),
        base_pe=pe_model.get("base_pe"),
        base_pe_source=pe_model.get("base_pe_source"),
        fair_pb=base_pb,
        required_fcf_yield_pct=base_fcf_req,
        hurdle_rate=pe_model.get("hurdle_rate"),
        confidence=_valuation_confidence(metrics, base_components, "generic"),
        drivers=pe_model.get("drivers") or [],
        note=(
            "Screening estimate from Yahoo Finance metrics. Fair P/E starts from the stock's actual traded P/E, "
            "then applies explicit premiums/discounts for quality, growth, cash conversion, leverage, beta, and peer sanity. "
            "Sector P/E is a reference check only; not a broker target or investment advice."
        ),
    )


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
        _metric("Volume", _fmt_metric_value(metrics.get("volume"), "number"), "number", period="latest session shares"),
        _metric("Avg Volume 10D", _fmt_metric_value(metrics.get("average_volume_10d") or metrics.get("average_volume"), "number"), "number",
                period="average daily shares"),
        _metric("Value Traded", _fmt_metric_value(metrics.get("traded_value"), "money"), "money", currency, "latest session"),
        _metric("Avg Daily Value", _fmt_metric_value(metrics.get("avg_daily_value_traded"), "money"), "money", currency, "10D/3M average"),
        _metric("Equity Liquidity", _fmt_metric_value(metrics.get("liquidity_pct"), "percent"), "percent",
                period="avg daily value / market cap"),
        _metric("Relative Volume 10D", _fmt_metric_value(metrics.get("relative_volume_10d"), "ratio"), "ratio",
                period="latest volume / 10D average"),
        _metric("TradingView Rating", _fmt_metric_value(metrics.get("recommend_all"), "ratio"), "ratio",
                period="-1 sell to +1 buy"),
        _metric("RSI", _fmt_metric_value(metrics.get("rsi"), "number"), "number", period="14-period technical"),
        _metric("Analyst Target Low", _fmt_metric_value(metrics.get("analyst_target_low"), "number"), "number", currency, "TradingView analyst consensus"),
        _metric("Analyst Target Median", _fmt_metric_value(metrics.get("analyst_target_median"), "number"), "number", currency, "TradingView analyst consensus"),
        _metric("Analyst Target High", _fmt_metric_value(metrics.get("analyst_target_high"), "number"), "number", currency, "TradingView analyst consensus"),
        _metric("24h Volume", _fmt_metric_value(metrics.get("volume_24h"), "money"), "money", currency, "24H"),
        _metric("Liquidity", _fmt_metric_value(metrics.get("liquidity_pct"), "percent"), "percent", period="24H volume / market cap"),
        _metric("1W Return", _fmt_metric_value(metrics.get("perf_1w"), "percent"), "percent", period="TradingView 1W performance"),
        _metric("1M Return", one_month, "percent", period=one_month_period),
        _metric("3M Return", _fmt_metric_value(metrics.get("perf_3m"), "percent"), "percent", period="TradingView 3M performance"),
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
    if mode in {"equity", "idx_screen"}:
        metric_rows = [m for m in metric_rows if m["label"] not in {"24h Volume", "Liquidity"}]
    elif mode == "crypto":
        equity_only = {"P/E", "Fwd P/E", "EV/EBITDA", "P/B", "Book Value", "Beta", "EPS", "ROE",
                       "Debt/Equity", "Revenue Growth", "EPS Growth", "Dividend Yield", "Gross Profit",
                       "Total Cash", "Free Cash Flow", "FCF Yield", "Volume", "Avg Volume 10D",
                       "Value Traded", "Avg Daily Value", "Equity Liquidity"}
        metric_rows = [m for m in metric_rows if m["label"] not in equity_only]
    valuation = metrics.get("_valuation_cached") if mode == "equity" else None
    if mode == "equity" and "_valuation_cached" not in metrics:
        valuation = _valuation(metrics)
    evidence_fields = {
        "equity": (
            "current_price", "market_cap", "pe", "forward_pe", "pb", "roe_pct",
            "debt_to_equity", "revenue_growth_pct", "eps_growth_pct", "fcf_yield_pct",
            "average_volume_10d", "liquidity_pct",
        ),
        "idx_screen": (
            "current_price", "market_cap", "volume", "average_volume_10d",
            "avg_daily_value_traded", "liquidity_pct", "relative_volume_10d",
            "recommend_all", "rsi", "perf_1w", "perf_3m", "volatility_1m",
        ),
        "crypto": ("current_price", "market_cap", "volume_24h", "liquidity_pct"),
    }.get(mode, ())
    input_valid = sum(1 for key in evidence_fields if _num(metrics.get(key)) is not None)
    input_coverage = round(input_valid / len(evidence_fields), 2) if evidence_fields else 0
    axis_coverage = round(len(valid) / len(axes), 2) if axes else 0
    return {
        "mode": mode,
        "schema_version": SCORE_SCHEMA_VERSION,
        "score": overall,
        "label": label,
        "coverage": input_coverage,
        "input_coverage": input_coverage,
        "axis_coverage": axis_coverage,
        "confidence": "High" if input_coverage >= 0.75 else "Medium" if input_coverage >= 0.5 else "Low",
        "axes": axes,
        "metrics": [m for m in metric_rows if m["value"] is not None],
        "valuation": valuation,
        "risk_stats": risk or None,
        "risk_context": ctx or None,
        "currency": currency,
        "source": metrics.get("source") or ("CoinGecko + price history" if mode == "crypto" else "Yahoo Finance"),
        "quote_source": metrics.get("quote_source"),
        "as_of": metrics.get("as_of") or _now_iso(),
        "data_warnings": metrics.get("_data_warnings") or [],
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
            "Volume": "volume", "Avg Volume 10D": "average_volume_10d",
            "Value Traded": "traded_value", "Avg Daily Value": "avg_daily_value_traded",
            "Equity Liquidity": "liquidity_pct",
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
    sector_pes, country_pes, country_sector_pes = {}, {}, {}
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
            country = row.get("country") or ""
            sector = row.get("sector_key") or ""
            sector_pes.setdefault(sector, []).append(pe)
            country_pes.setdefault(country, []).append(pe)
            country_sector_pes.setdefault((country, sector), []).append(pe)

    sector_peer_pe = {k: _median(v) for k, v in sector_pes.items() if len(v) >= 3}
    country_peer_pe = {k: _median(v) for k, v in country_pes.items() if len(v) >= 3}
    country_sector_peer_pe = {k: _median(v) for k, v in country_sector_pes.items() if len(v) >= 3}

    for row in rows:
        mode = "crypto" if row.get("country") == "CR" else "equity"
        risk_context = _risk_context(row, mode, risk_benchmarks)
        metrics = normalized_cache.get(row.get("source_symbol")) or metric_cache.get(row.get("source_symbol")) or {}
        if mode == "equity" and metrics:
            metrics = dict(metrics)
            country = row.get("country") or ""
            sector = row.get("sector_key") or ""
            peer = (country_sector_peer_pe.get((country, sector))
                    or sector_peer_pe.get(sector)
                    or country_peer_pe.get(country))
            if peer is not None:
                metrics["_sector_peer_pe"] = peer
                metrics["_sector_peer_pe_scope"] = (
                    f"{country} {sector} peer median" if country_sector_peer_pe.get((country, sector)) is not None
                    else f"mixed-market {sector} peer median" if sector_peer_pe.get(sector) is not None
                    else f"{country} market peer median"
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
                    {"key": "risk", "label": "Risk", "score": _score_low(_row_volatility(row), 1.2, 5.0)},
                ], {"source": "Price history only", "as_of": _now_iso(),
                    "_risk_context": risk_context,
                    "_risk_stats": _risk_stats(row, "equity", risk_context)},
                _spark_return(row.get("spark"), 22), _spark_return(row.get("spark")),
                _row_volatility(row))


def enrich_idx_screen(rows: list[dict], risk_benchmarks: dict | None = None) -> None:
    """Attach screen-grade TradingView scores to the expanded IDX universe."""
    for row in rows:
        if row.get("country") != "ID":
            continue
        existing = row.get("fundamental_score") or {}
        if row.get("source_provider") == "tradingview":
            if (row.get("data_tier") == "scored" and existing.get("score") is not None
                    and existing.get("source") != "Price history only"):
                existing["quote_source"] = "TradingView"
                existing["screen_source"] = "TradingView IDX scanner"
                continue
            row["fundamental_score"] = _score_idx_screen(row, risk_benchmarks)
        else:
            row["fundamental_score"] = _score_idx_fallback(row, risk_benchmarks)
