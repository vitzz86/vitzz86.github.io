"""What's Trending — finance social pulse + general search trends (keyless).

StockTwits trending symbols (tickers by social volume) + Google Trends daily RSS
for Indonesia and the US. Baked at cron time. Degrades to empty lists cleanly.
"""
from __future__ import annotations

import re
import sys
import urllib.request

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings


def _get(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def stocktwits() -> list:
    try:
        import json
        d = json.loads(_get(settings.STOCKTWITS_TRENDING))
        out = []
        for s in d.get("symbols", [])[:12]:
            sym = s.get("symbol", "")
            out.append({
                "symbol": sym,
                "name": s.get("title", ""),
                # crypto symbols come as X.X (e.g. ETH.X); link plain ones to Yahoo
                "url": ("https://stocktwits.com/symbol/" + sym),
            })
        return out
    except Exception as e:  # noqa: BLE001
        print(f"[trending] stocktwits failed: {e}")
        return []


def google_trends(geo: str) -> list:
    try:
        xml = _get(settings.GOOGLE_TRENDS_RSS + geo)
        titles = re.findall(r"<title>(.*?)</title>", xml, re.S)
        # first <title> is the channel name; skip it
        items = [re.sub(r"<!\[CDATA\[|\]\]>", "", t).strip() for t in titles[1:9]]
        return [t for t in items if t]
    except Exception as e:  # noqa: BLE001
        print(f"[trending] google trends {geo} failed: {e}")
        return []


def collect() -> dict:
    out = {
        "tickers": stocktwits(),
        "trends_id": google_trends("ID"),
        "trends_us": google_trends("US"),
    }
    print(f"[trending] {len(out['tickers'])} tickers, "
          f"{len(out['trends_id'])} ID / {len(out['trends_us'])} US trends")
    return out
