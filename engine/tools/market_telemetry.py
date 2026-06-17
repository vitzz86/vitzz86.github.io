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
    from tools import yquote

    quotes = yquote.fetch([sym for sym, _, _ in settings.TICKERS])
    try:
        from tools import crypto_quotes
        for sym, row in crypto_quotes.simple([sym for sym, _, kind in settings.TICKERS
                                              if kind == "crypto"]).items():
            quotes.setdefault(sym, {}).update(row)
    except Exception as e:  # noqa: BLE001
        print(f"[market_telemetry] CoinGecko crypto overlay failed: {e}")
    rows, anomaly_bits = [], []
    for symbol, label, kind in settings.TICKERS:
        r = quotes.get(symbol)
        if not r:
            print(f"[market_telemetry] {symbol} — no quote this run")
            continue
        delta = r["delta_pct"]
        rows.append({
            "symbol": symbol,
            "label": label,
            "kind": kind,
            "value": round(r["value"], 2),
            "delta_pct": delta,
            "prev_close": round(r["prev_close"], 2),
            "state": "open" if r["open"] else "closed",
            "mkt_start": r.get("mkt_start"),
            "mkt_end": r.get("mkt_end"),
            "spark": r.get("spark", []),
            "intraday": r.get("intraday", []),
            "url": ("https://www.coingecko.com/en/coins/bitcoin"
                    if symbol == "BTC-USD" else settings.YF_QUOTE + symbol),
        })
        if symbol in settings.ANOMALY_WATCHLIST and abs(delta) > settings.ANOMALY_THRESHOLD_PCT:
            direction = "drop" if delta < 0 else "spike"
            anomaly_bits.append(f"{label} {direction} of {delta:+.2f}%")

    return {
        "rows": rows,
        "anomaly": bool(anomaly_bits),
        "anomaly_desc": "; ".join(anomaly_bits),
    }
