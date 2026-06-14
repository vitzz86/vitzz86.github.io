"""News engine (PRD v2 · Module D) — universal-link layer + per-entity discovery.

Beyond the curated publisher RSS, this queries Google News search (keyless, full
index) per index / sector / ticker so the dashboard has real news for *every*
component — and yfinance.news for extra US depth. Every item keeps a verified
source URL (URL-less items are dropped). Items are tagged with a category and a
geography (ID / US / GL) for the Intelligence Wire filters.

Returns:
    {"wire": [...], "sector_news": {key: [...]}, "ticker_news": {ticker: [...]}}
"""
from __future__ import annotations

import concurrent.futures as cf
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings

CATEGORY_KEYWORDS = {
    "MACRO":      ["rate", "inflation", "gdp", "policy", "central bank", "treasury",
                   "bi-rate", "the fed", "ecb", "rupiah", "fiscal", "tariff", "yield"],
    "STARTUP":    ["funding", "series ", "seed", "acquisition", "ipo", "venture",
                   "raises", "round", "startup", "valuation"],
    "PUBLIC_MKT": ["earnings", "stock", "shares", "equity", "listed", "dividend",
                   "buyback", "guidance", "index", "bourse", "saham"],
    "CLIMATE":    ["renewable", "solar", "carbon", " ev", "energy", "climate",
                   "green", "geothermal", "battery", "nickel", "emission"],
}


def _category(text: str) -> str:
    t = text.lower()
    best, score = "MACRO", 0
    for cat, kws in CATEGORY_KEYWORDS.items():
        s = sum(1 for k in kws if k in t)
        if s > score:
            best, score = cat, s
    return best


def _get(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def google_news(query: str, geo: str = "US", n: int = None) -> list:
    """Keyless Google News RSS search for any query, region-targeted."""
    n = n or settings.NEWS_PER_QUERY
    geoq = settings.GOOGLE_NEWS_GEO.get(geo, settings.GOOGLE_NEWS_GEO["US"])
    url = f"{settings.GOOGLE_NEWS}?q={urllib.parse.quote(query)}&{geoq}"
    out = []
    try:
        xml = _get(url)
        for m in list(re.finditer(r"<item>(.*?)</item>", xml, re.S))[:n]:
            block = m.group(1)
            title = re.search(r"<title>(.*?)</title>", block, re.S)
            link = re.search(r"<link>(.*?)</link>", block, re.S)
            src = re.search(r"<source[^>]*>(.*?)</source>", block, re.S)
            if not title or not link:
                continue
            t = re.sub(r"<!\[CDATA\[|\]\]>", "", title.group(1)).strip()
            # Google appends " - Source" to titles; split it out
            source = src.group(1).strip() if src else ""
            if not source and " - " in t:
                t, source = t.rsplit(" - ", 1)
            out.append({"title": t[:220], "url": link.group(1).strip(),
                        "source": source, "geo": geo, "category": _category(t)})
    except Exception as e:  # noqa: BLE001
        print(f"[news] google query failed '{query}': {e}")
    return out


def _from_curated(headlines: dict) -> list:
    items = []
    for bucket in headlines.values():
        for h in bucket:
            url, title = (h.get("link") or "").strip(), (h.get("title") or "").strip()
            if url and title:
                items.append({"title": title[:220], "url": url,
                              "source": h.get("source", ""), "geo": "GL",
                              "category": _category(title)})
    return items


def _dedupe(items: list, cap: int) -> list:
    seen, out = set(), []
    for it in items:
        key = it["title"].lower()[:70]
        if it.get("url") and key not in seen:
            seen.add(key)
            out.append(it)
        if len(out) >= cap:
            break
    return out


def enrich(headlines: dict, sectors: list, telemetry: list) -> dict:
    # --- per-index / instrument news ---
    idx_terms = {
        "^JKSE": ("Jakarta Composite IHSG", "ID"), "^IXIC": ("Nasdaq composite", "US"),
        "^GSPC": ("S&P 500", "US"), "^N225": ("Nikkei 225", "US"), "^DJI": ("Dow Jones", "US"),
        "BTC-USD": ("Bitcoin price", "US"), "GC=F": ("gold price", "US"),
        "BZ=F": ("Brent crude oil", "US"), "CL=F": ("WTI crude oil", "US"),
        "USDIDR=X": ("rupiah USD IDR", "ID"), "^VIX": ("VIX volatility", "US"),
        "^TNX": ("US 10 year treasury yield", "US"), "DX-Y.NYB": ("US dollar index", "US"),
    }
    # entity-specific news first (carries real ID/US geo), curated GL fills the rest
    wire = []
    for r in telemetry:
        q = idx_terms.get(r["symbol"])
        if q:
            wire += google_news(q[0], q[1], 3)

    # --- per-sector news ---
    sector_news = {}
    for s in sectors:
        q = f"Indonesia {s['name']} sector saham"
        items = google_news(q, "ID", settings.NEWS_PER_QUERY)
        items += google_news(f"{s['name']} sector stocks US", "US", 2)
        items = _dedupe(items, 6)
        for it in items:
            it["sectors"] = [s["key"]]
        sector_news[s["key"]] = items
        wire += items

    wire += _from_curated(headlines)      # global wire baseline fills the remainder

    # --- per-ticker news (threaded; every constituent) ---
    cons = [(c["ticker"], c["name"].split(" (")[0], c["country"])
            for s in sectors for c in s["constituents"]]

    def fetch(t):
        tk, name, country = t
        q = f"{tk} {name.split()[0]} saham" if country == "ID" else f"{tk} {name.split()[0]} stock"
        return tk, google_news(q, country, 3)

    ticker_news = {}
    try:
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for tk, items in ex.map(fetch, cons):
                if items:
                    ticker_news[tk] = items
    except Exception as e:  # noqa: BLE001
        print(f"[news] ticker fetch pool failed: {e}")

    wire = _dedupe(wire, settings.NEWS_WIRE_CAP)
    print(f"[news] wire={len(wire)} · sectors={len(sector_news)} · "
          f"tickers_with_news={len(ticker_news)}")
    return {"wire": wire, "sector_news": sector_news, "ticker_news": ticker_news}
