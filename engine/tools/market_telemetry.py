"""Agent 1 ingestion surface: numeric market telemetry via yfinance.

Pure-python variance checks — no LLM. Emits the telemetry rows for the
dashboard's Quant card plus the Market Anomaly Event flag that reshapes the
OSINT hunter's queries downstream.
"""
import sys

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings


def collect() -> dict:
    """Returns {"rows": [...], "anomaly": bool, "anomaly_desc": str}."""
    import yfinance as yf

    rows, anomaly_bits = [], []
    for symbol, label, kind in settings.TICKERS:
        try:
            hist = yf.Ticker(symbol).history(period="1mo", interval="1d")
            closes = hist["Close"].dropna()
            if len(closes) < 2:
                raise ValueError("insufficient history")
            value, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
            delta = (value - prev) / prev * 100
            series = [round(float(c), 4) for c in closes.tolist()[-20:]]
            rows.append({
                "symbol": symbol,
                "label": label,
                "kind": kind,
                "value": round(value, 2),
                "delta_pct": round(delta, 2),
                "spark": series,
                "url": settings.YF_QUOTE + symbol,
            })
            if symbol in settings.ANOMALY_WATCHLIST and abs(delta) > settings.ANOMALY_THRESHOLD_PCT:
                direction = "drop" if delta < 0 else "spike"
                anomaly_bits.append(f"{label} {direction} of {delta:+.2f}%")
        except Exception as e:  # noqa: BLE001 — a dead ticker must not kill the run
            print(f"[market_telemetry] {symbol} failed: {e}")

    return {
        "rows": rows,
        "anomaly": bool(anomaly_bits),
        "anomaly_desc": "; ".join(anomaly_bits),
    }
