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
import datetime as dt
import email.utils
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings

# Intelligence Wire taxonomy v3: Economy · Tech · Markets & Finance · Crypto.
CATEGORY_KEYWORDS = {
    "CRYPTO":          ["bitcoin", "ethereum", "crypto", "blockchain", "token", "defi",
                        "solana", "btc", "eth", "stablecoin", "altcoin", "web3", "binance"],
    "TECH":            ["ai", "artificial intelligence", "startup", "venture", "funding",
                        "series ", "seed", "software", "chip", "semiconductor", "cloud",
                        "saas", "app", "data center", "nvidia", "openai", "google",
                        "apple", "microsoft", "meta", "gojek", "goto", "digital", "tech"],
    "MARKETS_FINANCE": ["stock", "shares", "equity", "earnings", "dividend", "ipo", "bond",
                        "yield", "treasury", "gold", "oil", "commodity", "nickel", "coal",
                        "saham", "ihsg", "bourse", "index", "buyback", "bank", "valuation"],
    "ECONOMY":         ["rate", "inflation", "gdp", "economy", "central bank", "the fed",
                        "bi-rate", "fiscal", "tariff", "trade", "jobs", "employment",
                        "rupiah", "policy", "deficit", "budget", "recession", "ekonomi"],
}
DEFAULT_CATEGORY = "ECONOMY"


def _category(text: str) -> str:
    t = text.lower()
    best, score = DEFAULT_CATEGORY, 0
    for cat, kws in CATEGORY_KEYWORDS.items():
        s = sum(1 for k in kws if k in t)
        if s > score:
            best, score = cat, s
    return best


def _get(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _parse_ts(s: str) -> int:
    try:
        return int(email.utils.parsedate_to_datetime(s.strip()).timestamp())
    except Exception:  # noqa: BLE001
        return 0


def _now() -> int:
    return int(dt.datetime.now(dt.timezone.utc).timestamp())


def _clean_html(s: str) -> str:
    s = re.sub(r"<!\[CDATA\[|\]\]>", "", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def google_news(query: str, geo: str = "US", n: int = None, category: str = None) -> list:
    """Keyless Google News RSS search for any query, region-targeted.
    category: force a taxonomy label (else auto-classified from the headline)."""
    n = n or settings.NEWS_PER_QUERY
    geoq = settings.GOOGLE_NEWS_GEO.get(geo, settings.GOOGLE_NEWS_GEO["US"])
    q = query + " when:7d"        # Google News recency operator → last 7 days only
    url = f"{settings.GOOGLE_NEWS}?q={urllib.parse.quote(q)}&{geoq}"
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
            pd = re.search(r"<pubDate>(.*?)</pubDate>", block, re.S)
            ts = _parse_ts(pd.group(1)) if pd else 0
            desc = re.search(r"<description>(.*?)</description>", block, re.S)
            summary = _clean_html(desc.group(1)) if desc else ""
            # Google's RSS description is a related-headlines list — keep it only when
            # it adds real prose beyond the title; otherwise leave blank for the client.
            if summary and (summary[:40].lower() == t[:40].lower() or len(summary) < 60):
                summary = ""
            out.append({"title": t[:220], "url": link.group(1).strip(),
                        "source": source, "geo": geo,
                        "category": category or _category(t),
                        "summary": summary[:400], "ts": ts})
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


WEEK = 7 * 86400


def _recent(items: list, cap: int = None) -> list:
    """Keep items from the last 7 days, newest first (today prioritized)."""
    now = _now()
    fresh = [it for it in items if it.get("ts") and (now - it["ts"]) <= WEEK]
    fresh.sort(key=lambda it: it["ts"], reverse=True)
    return fresh[:cap] if cap else fresh


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

    # broad per-geo topic fan across the Economy/Tech/Markets/Crypto taxonomy — this is
    # the volume driver that lifts the wire to ~100 items per region (threaded).
    topic_jobs = [(q, geo, cat) for geo, lst in settings.WIRE_TOPICS.items()
                  for q, cat in lst]

    def _topic(job):
        q, geo, cat = job
        return google_news(q, geo, settings.NEWS_TOPIC_PER_QUERY, category=cat)

    try:
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for items in ex.map(_topic, topic_jobs):
                wire += items
    except Exception as e:  # noqa: BLE001
        print(f"[news] topic fan failed: {e}")

    # --- per-sector news (richer, sector-tuned queries; recency-biased) ---
    # (us_query, id_query) — tuned to the actual trending angle of each sector
    SQ = {
        "technology":   ("AI technology stocks Nvidia data center", "saham teknologi AI Indonesia"),
        "financials":   ("bank stocks rates earnings", "saham bank Indonesia BBCA BBRI"),
        "energy":       ("nickel coal mining energy stocks", "saham tambang batu bara nikel"),
        "renewables":   ("solar renewable energy stocks clean", "energi terbarukan saham hijau Indonesia"),
        "consumer":     ("consumer staples retail stocks", "saham konsumer ritel Indonesia"),
        "infrastructure":("infrastructure construction stocks", "saham infrastruktur konstruksi Indonesia"),
        "healthcare":   ("healthcare pharma biotech stocks", "saham farmasi kesehatan Indonesia"),
        "logistics":    ("logistics shipping freight stocks", "saham logistik pelayaran Indonesia"),
        "entertainment":("media streaming entertainment stocks", "saham media hiburan Indonesia"),
        "property":     ("real estate property REIT stocks", "saham properti real estate Indonesia"),
        "crypto":       ("bitcoin ethereum crypto market", "kripto bitcoin pasar"),
    }
    sector_news = {}
    for s in sectors:
        usq, idq = SQ.get(s["key"], (f"{s['name']} stocks", f"saham {s['name']} Indonesia"))
        items = google_news(usq, "US", 5) + google_news(idq, "ID", 5)
        items = _recent(_dedupe(items, 14))   # ≤7 days, newest first
        for it in items:
            it["sectors"] = [s["key"]]
        sector_news[s["key"]] = items[:8]
        wire += items[:5]

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
                items = _recent(items, 4)        # ≤7d, newest first, top 4
                if items:
                    ticker_news[tk] = items
    except Exception as e:  # noqa: BLE001
        print(f"[news] ticker fetch pool failed: {e}")

    # balance roughly 50/50 ID/US so neither region starves the wire
    fresh = _recent(wire)                       # ≤7d, newest first
    half = settings.NEWS_WIRE_CAP // 2
    id_w = _dedupe([x for x in fresh if x.get("geo") == "ID"], half)
    us_w = _dedupe([x for x in fresh if x.get("geo") != "ID"], settings.NEWS_WIRE_CAP - half)
    wire = sorted(id_w + us_w, key=lambda x: x.get("ts", 0), reverse=True)
    print(f"[news] wire={len(wire)} (≤7d · {len(id_w)} ID / {len(us_w)} US) · "
          f"sectors={len(sector_news)} · tickers_with_news={len(ticker_news)}")
    return {"wire": wire, "sector_news": sector_news, "ticker_news": ticker_news}
