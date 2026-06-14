"""Market Movers + social trending (keyless).

Gainers / losers / most-active are computed from our own 200-ticker universe
(reliable, already fetched) split by market — Google Finance is JS-rendered and
can't be scraped server-side. StockTwits adds a US social-buzz list.
"""
from __future__ import annotations

import json
import sys
import urllib.request

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings


def _get(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def stocktwits() -> list:
    try:
        d = json.loads(_get(settings.STOCKTWITS_TRENDING))
        return [{"symbol": s.get("symbol", ""), "name": s.get("title", ""),
                 "url": "https://stocktwits.com/symbol/" + s.get("symbol", "")}
                for s in d.get("symbols", [])[:12]]
    except Exception as e:  # noqa: BLE001
        print(f"[trending] stocktwits failed: {e}")
        return []


def _movers(rows: list) -> dict:
    """rows: flat list of constituent dicts with delta_pct/turnover/country/url."""
    def trim(items):
        return [{"ticker": r["ticker"], "name": r["name"], "country": r["country"],
                 "delta_pct": r["delta_pct"], "url": r["url"]} for r in items]
    by_g = sorted(rows, key=lambda r: r["delta_pct"], reverse=True)
    by_a = sorted(rows, key=lambda r: r.get("turnover", 0), reverse=True)
    return {
        "gainers": trim(by_g[:8]),
        "losers": trim(list(reversed(by_g))[:8]),
        "active": trim(by_a[:8]),
    }


def collect(sectors_list: list) -> dict:
    rows = [c for s in sectors_list for c in s["constituents"]]
    id_rows = [r for r in rows if r["country"] == "ID"]
    us_rows = [r for r in rows if r["country"] == "US"]
    out = {
        "id": _movers(id_rows),
        "us": _movers(us_rows),
        "social": stocktwits(),
    }
    print(f"[trending] movers from {len(rows)} tickers "
          f"({len(id_rows)} ID / {len(us_rows)} US) + {len(out['social'])} social")
    return out
