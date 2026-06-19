"""Market Movers + social trending (keyless).

Gainers / losers / top-score names are computed from our own universe
(reliable, already fetched) split by market. Google Finance is JS-rendered and
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


def _score(row: dict) -> float:
    val = (row.get("fundamental_score") or {}).get("score")
    try:
        return float(val)
    except Exception:  # noqa: BLE001
        return -1.0


def _dedupe(rows: list) -> list:
    """Keep one row per ticker/country so duplicate sector memberships do not crowd movers."""
    out: dict[tuple, dict] = {}
    for row in rows:
        key = (row.get("country"), row.get("ticker"))
        if key not in out:
            out[key] = row
            continue
        cur = out[key]
        # Prefer the version with the richer score payload, then the larger absolute move.
        if _score(row) > _score(cur) or (
            _score(row) == _score(cur)
            and abs(float(row.get("delta_pct") or 0)) > abs(float(cur.get("delta_pct") or 0))
        ):
            out[key] = row
    return list(out.values())


def _movers(rows: list) -> dict:
    """rows: flat list of constituent dicts with delta_pct/turnover/country/url."""
    def trim(items):
        out = []
        for r in items:
            fs = r.get("fundamental_score") or {}
            out.append({
                "ticker": r["ticker"],
                "name": r["name"],
                "country": r["country"],
                "delta_pct": r["delta_pct"],
                "url": r["url"],
                "score": fs.get("score"),
                "score_label": fs.get("label"),
            })
        return out

    rows = _dedupe(rows)
    by_g = sorted(rows, key=lambda r: r["delta_pct"], reverse=True)
    by_a = sorted(rows, key=lambda r: r.get("turnover", 0), reverse=True)
    by_s = sorted([r for r in rows if _score(r) >= 0], key=_score, reverse=True)
    return {
        "gainers": trim(by_g[:8]),
        "losers": trim(list(reversed(by_g))[:8]),
        "top_score": trim(by_s[:8]),
        # Compatibility for older frontends that still ask for active.
        "active": trim(by_a[:8]),
    }


def collect(sectors_list: list) -> dict:
    rows = [c for s in sectors_list for c in s["constituents"]]
    id_rows = [r for r in rows if r["country"] == "ID"]
    us_rows = [r for r in rows if r["country"] == "US"]
    crypto_rows = [r for r in rows if r["country"] == "CR"]
    other_rows = [r for r in rows if r.get("region") == "OTHERS"]
    out = {
        "id": _movers(id_rows),
        "us": _movers(us_rows),
        "others": _movers(other_rows),
        "crypto": _movers(crypto_rows),
        "social": stocktwits(),
    }
    print(f"[trending] movers from {len(rows)} tickers "
          f"({len(id_rows)} ID / {len(us_rows)} US / {len(other_rows)} others / "
          f"{len(crypto_rows)} crypto) "
          f"+ {len(out['social'])} social")
    return out
