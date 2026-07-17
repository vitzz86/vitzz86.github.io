"""Agent 1 ingestion surface: numeric market telemetry via yfinance.

Pure-python variance checks — no LLM. Emits the telemetry rows for the
dashboard's Quant card plus the Market Anomaly Event flag that reshapes the
OSINT hunter's queries downstream.
"""
import sys

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings


def collect() -> dict:
    """Returns {"rows": [...], "anomaly": bool, "anomaly_desc": str}.

    Prices/% come from Yahoo's v8 quote (tools.yquote) — the value, official prior
    close and daily % exactly as Yahoo/Bloomberg show, plus open/closed state."""
    from tools import macro_rates, yquote

    quotes = yquote.fetch([sym for sym, _, _ in settings.TICKERS])
    try:
        from tools import crypto_quotes
        for sym, row in crypto_quotes.simple([sym for sym, _, kind in settings.TICKERS
                                              if kind == "crypto"]).items():
            quotes.setdefault(sym, {}).update(row)
    except Exception as e:  # noqa: BLE001
        print(f"[market_telemetry] CoinGecko crypto overlay failed: {e}")
    try:
        quotes.update(macro_rates.collect())
    except Exception as e:  # noqa: BLE001
        print(f"[market_telemetry] macro-rate overlay failed: {e}")
    rows, anomaly_bits = [], []
    for symbol, label, kind in settings.TICKERS:
        r = quotes.get(symbol)
        if not r:
            print(f"[market_telemetry] {symbol} — no quote this run")
            continue
        value = float(r["value"])
        prev_close = float(r["prev_close"])
        value_unit = r.get("value_unit")
        delta_unit = r.get("delta_unit", "percent")
        delta = float(r["delta_pct"])
        if symbol in {"^IRX", "^TNX"}:
            value_unit = "percent"
            delta_unit = "bp"
            delta = round((value - prev_close) * 100, 1)
        rows.append({
            "symbol": symbol,
            "label": label,
            "kind": kind,
            "value": round(value, 3 if value_unit == "percent" else 2),
            "value_unit": value_unit,
            "delta_pct": delta,
            "delta_unit": delta_unit,
            "prev_close": round(prev_close, 3 if value_unit == "percent" else 2),
            "state": "open" if r["open"] else "closed",
            "mkt_start": r.get("mkt_start"),
            "mkt_end": r.get("mkt_end"),
            "quote_asof": r.get("quote_asof"),
            "quote_mode": r.get("quote_mode", "provider_snapshot"),
            "spark": r.get("spark", []),
            "spark_ts": r.get("spark_ts", []),
            "intraday": r.get("intraday", []),
            "chart_quality": r.get("chart_quality"),
            "chart_asof": r.get("chart_asof"),
            "url": ("https://www.coingecko.com/en/coins/bitcoin"
                    if symbol == "BTC-USD" else settings.YF_QUOTE + symbol),
        })
        if symbol in settings.ANOMALY_WATCHLIST and abs(delta) > settings.ANOMALY_THRESHOLD_PCT:
            direction = "drop" if delta < 0 else "spike"
            anomaly_bits.append(f"{label} {direction} of {delta:+.2f}%")

        if symbol == "USDIDR=X":
            for msym, mlabel, mkind in settings.MACRO_RATE_BENCHMARKS:
                mr = quotes.get(msym)
                if not mr:
                    print(f"[market_telemetry] {msym} — no macro-rate quote this run")
                    continue
                rows.append({
                    "symbol": msym,
                    "label": mlabel,
                    "kind": mkind,
                    "value": round(float(mr["value"]), 3),
                    "value_unit": mr.get("value_unit", "percent"),
                    "delta_pct": float(mr.get("delta_pct") or 0.0),
                    "delta_unit": mr.get("delta_unit", "bp"),
                    "prev_close": round(float(mr.get("prev_close", mr["value"])), 3),
                    "state": mr.get("state", "closed"),
                    "mkt_start": mr.get("mkt_start"),
                    "mkt_end": mr.get("mkt_end"),
                    "spark": mr.get("spark", []),
                    "spark_ts": mr.get("spark_ts", []),
                    "intraday": mr.get("intraday", []),
                    "url": mr.get("url"),
                    "source_name": mr.get("source_name"),
                    "asof": mr.get("asof"),
                })

    return {
        "rows": rows,
        "anomaly": bool(anomaly_bits),
        "anomaly_desc": "; ".join(anomaly_bits),
    }
