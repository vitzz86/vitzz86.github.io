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
import json
import os
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

TRUSTED_BY_DOMAIN = {
    domain: (group, name)
    for group, rows in settings.NEWS_TRUSTED_SOURCES.items()
    for name, domain in rows
}
TRUSTED_BY_NAME = {
    name.lower(): (group, domain)
    for group, rows in settings.NEWS_TRUSTED_SOURCES.items()
    for name, domain in rows
}
SOURCE_TIER_SCORE = {
    "tier1_global": 45, "official": 45, "indonesia": 40,
    "apac_sea": 35, "crypto": 30, "us_equity": 20,
}


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


import html as _html  # noqa: E402


def _clean_html(s: str) -> str:
    s = re.sub(r"<!\[CDATA\[|\]\]>", "", s or "")
    s = _html.unescape(s)              # decode &lt;a&gt; → <a> (Google News double-encodes)
    s = re.sub(r"<[^>]+>", " ", s)     # strip the now-real tags
    s = _html.unescape(s)              # &nbsp; → space, any residual entities
    return re.sub(r"\s+", " ", s).strip()


def _trusted_meta(source: str, site: str = "") -> tuple[str, int]:
    site = (site or "").lower()
    source_l = (source or "").lower()
    if site in TRUSTED_BY_DOMAIN:
        group, _name = TRUSTED_BY_DOMAIN[site]
        return group, SOURCE_TIER_SCORE.get(group, 0)
    for name, (group, _domain) in TRUSTED_BY_NAME.items():
        if name and (name in source_l or source_l in name):
            return group, SOURCE_TIER_SCORE.get(group, 0)
    return "", 0


def google_news(query: str, geo: str = "US", n: int = None, category: str = None,
                site: str = "", query_type: str = "discovery") -> list:
    """Keyless Google News RSS search for any query, region-targeted.
    category: force a taxonomy label (else auto-classified from the headline)."""
    n = n or settings.NEWS_PER_QUERY
    geoq = settings.GOOGLE_NEWS_GEO.get(geo, settings.GOOGLE_NEWS_GEO["US"])
    q = query + (f" site:{site}" if site else "") + " when:7d"
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
            t = _clean_html(title.group(1))
            # Google appends " - Source" to titles; split it out
            source = _clean_html(src.group(1)) if src else ""
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
            tier, boost = _trusted_meta(source, site)
            out.append({"title": t[:220], "url": link.group(1).strip(),
                        "source": source, "geo": geo,
                        "category": category or _category(t),
                        "summary": summary[:400], "ts": ts,
                        "source_tier": tier, "source_score": boost,
                        "query_type": query_type,
                        "query": query, "target_site": site})
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
    fresh.sort(key=lambda it: (it.get("score", 0), it["ts"]), reverse=True)
    return fresh[:cap] if cap else fresh


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


NOISE_TITLE_PATTERNS = (
    "top pro news",
    "bloomberg businessweek",
    "crypto bloomberg com",
    "markets bloomberg com",
    "technology bloomberg com",
    "stocks bloomberg com",
    "sector industry performance",
    "sector amp industry performance",
    "stock price news quote history",
    "stock price news quote amp history",
    "stock price stock chart market cap news today",
    "stock price stock chart market cap amp news today",
    "money personal investing",
    "personal investing",
    "stock price latest news reuters",
    "commodities trading gold stocks oil stocks silver natural gas",
    "legality of cryptocurrency by country or territory",
)

NOISE_TITLE_REGEX = (
    r"^watch\s+",
    r"^about\s+[a-z0-9.()\-]+\s*$",
    r"^about\s+.+\s+reuters$",
    r"^[a-z0-9.()\-]+\s+reuters$",
    r"^\([a-z0-9.()\-]+\)\s+stock price.+reuters$",
)

SECTOR_RELEVANCE_TERMS = {
    "technology": [
        "ai", "artificial intelligence", "semiconductor", "chip", "data center",
        "cloud", "software", "digital", "fintech", "nvidia", "openai", "teknologi",
        "kecerdasan buatan", "pusat data",
    ],
    "financials": [
        "bank", "banks", "banking", "lending", "loan", "credit", "rate", "rates",
        "net interest", "jpmorgan", "goldman", "bbca", "bbri", "bmri", "suku bunga",
        "perbankan", "kredit",
    ],
    "energy": [
        "coal", "nickel", "copper", "oil", "gas", "mining", "miner", "commodity",
        "commodities", "tambang", "batubara", "batu bara", "nikel", "energi",
    ],
    "renewables": [
        "renewable", "renewables", "clean energy", "solar", "wind", "geothermal",
        "battery", "ev", "electric vehicle", "climate tech", "carbon", "grid",
        "energi terbarukan", "panas bumi", "surya", "hijau", "pgeo", "essa", "batr",
    ],
    "consumer": [
        "consumer", "retail", "staples", "fmcg", "ecommerce", "restaurant", "food",
        "beverage", "ritel", "konsumer", "konsumsi", "makanan", "minuman",
    ],
    "infrastructure": [
        "infrastructure", "construction", "toll road", "cement", "contractor",
        "capex", "infrastruktur", "konstruksi", "jalan tol", "semen",
    ],
    "healthcare": [
        "healthcare", "health", "pharma", "biotech", "medical", "hospital", "drug",
        "kesehatan", "farmasi", "rumah sakit", "obat",
    ],
    "logistics": [
        "logistics", "shipping", "freight", "port", "transport", "airline",
        "supply chain", "logistik", "pelayaran", "pelabuhan", "transportasi",
    ],
    "entertainment": [
        "media", "streaming", "gaming", "film", "advertising", "entertainment",
        "consumer services", "hiburan", "iklan", "game",
    ],
    "property": [
        "property", "real estate", "reit", "housing", "mortgage", "developer",
        "properti", "perumahan", "apartemen",
    ],
    "crypto": [
        "bitcoin", "ethereum", "crypto", "cryptocurrency", "blockchain", "token",
        "stablecoin", "defi", "etf", "binance", "solana", "xrp", "kripto",
    ],
}

LOW_CONF_SOURCES = (
    "24/7 wall st", "simplywall", "simply wall", "cryptorank",
    "latest news from azerbaijan", "blockchain council",
)

MARKET_ANCHOR_TERMS = (
    "stock", "stocks", "share", "shares", "equity", "market", "markets",
    "sector", "industry", "earnings", "revenue", "profit", "margin", "guidance",
    "ipo", "deal", "m&a", "merger", "acquisition", "buyout", "valuation",
    "dividend", "bond", "yield", "fund", "investor", "investment", "capital",
    "price", "prices", "target", "rating", "upgrade", "downgrade", "saham",
    "emiten", "ihsg", "bei", "bursa", "pendapatan", "laba", "akuisisi",
    "investasi", "obligasi",
)

SECTOR_ANCHOR_TERMS = {
    "technology": ("capex", "chips", "compute", "server", "model", "platform"),
    "financials": ("loan", "loans", "deposit", "deposits", "credit", "nim"),
    "energy": ("supply", "demand", "production", "export", "inventory", "smelter"),
    "renewables": ("capacity", "project", "projects", "power", "electricity", "tariff", "policy"),
    "consumer": ("sales", "demand", "pricing", "brand", "store", "stores"),
    "infrastructure": ("project", "projects", "contract", "contracts", "construction", "capex"),
    "healthcare": ("trial", "drug", "therapy", "hospital", "approval", "patients"),
    "logistics": ("freight", "shipping", "shipment", "shipments", "transport", "port", "cargo", "trucking"),
    "entertainment": ("streaming", "subscriber", "subscribers", "advertising", "content", "gaming"),
    "property": ("reit", "rent", "rental", "office", "housing", "mortgage", "mall"),
    "crypto": ("price", "trading", "trader", "regulation", "regulator", "etf", "stablecoin"),
}

QUERY_STOPWORDS = {
    "stock", "stocks", "market", "markets", "news", "price", "prices", "shares",
    "economy", "economic", "global", "outlook", "report", "today", "week",
    "indonesia", "indonesian", "saham", "emiten", "bursa", "efek",
}


def _is_noise_item(it: dict) -> bool:
    title = _norm(it.get("title", ""))
    if not title:
        return True
    if any(p in title for p in NOISE_TITLE_PATTERNS):
        return True
    return any(re.search(p, title) for p in NOISE_TITLE_REGEX)


def _normalize_item(it: dict) -> dict:
    it = dict(it)
    for k in ("title", "source", "summary"):
        if isinstance(it.get(k), str):
            it[k] = _clean_html(it[k])
    return it


def _query_terms(it: dict) -> list[str]:
    q = _norm(it.get("query", ""))
    return [w for w in q.split() if len(w) > 3 and w not in QUERY_STOPWORDS][:8]


def _dedupe_key(it: dict) -> tuple:
    url = (it.get("url") or "").strip()
    # Google News wrapper URLs are unique enough for click-through, but related wire
    # copies need title/source collapse too.
    return (url, _norm(it.get("title", ""))[:90], _norm(it.get("source", ""))[:40])


def _dedupe(items: list, cap: int) -> list:
    seen_url, seen_title, out = set(), set(), []
    for it in items:
        url, title, source = _dedupe_key(it)
        title_key = (title, source)
        if it.get("url") and url not in seen_url and title_key not in seen_title:
            seen_url.add(url)
            seen_title.add(title_key)
            out.append(it)
        if len(out) >= cap:
            break
    return out


def _score_item(it: dict, terms: list[str] = None, trusted_bias: int = 0) -> dict:
    it = _normalize_item(it)
    txt = _norm(" ".join([it.get("title", ""), it.get("summary", ""), it.get("source", "")]))
    terms = [_norm(t) for t in (terms if terms is not None else _query_terms(it)) if t]
    relevance = 0
    for t in terms:
        if not t:
            continue
        if len(t) <= 5:
            relevance += 18 if re.search(rf"\b{re.escape(t)}\b", txt) else 0
        elif t in txt:
            relevance += 12
    age = max(0, _now() - int(it.get("ts") or 0))
    fresh = 25 if age <= 86400 else 15 if age <= 3 * 86400 else 5
    query_bonus = {"trusted": 20, "official": 18, "gap": 10, "ticker": 8,
                   "sector": 7, "topic": 5, "index": 5}.get(it.get("query_type"), 0)
    score = int(it.get("source_score", 0)) + trusted_bias + relevance + fresh + query_bonus
    title_l = (it.get("title") or "").lower()
    if "opinion" in title_l or "op-ed" in title_l:
        score -= 8
    source_l = _norm(it.get("source", ""))
    if any(s in source_l for s in LOW_CONF_SOURCES):
        score -= 14
    if it.get("geo") == "ID":
        id_terms = ("indonesia", "rupiah", "ihsg", "idx", "bei", "saham", "emiten",
                    "bank indonesia", "ojk", "apbn", "jakarta", "bursa")
        if not any(t in txt for t in id_terms):
            score -= 18
    if not relevance and not it.get("source_score") and it.get("query_type") in {"ticker", "gap"}:
        score -= 18
    it["score"] = score
    return it


def _rank(items: list, cap: int, terms: list[str] = None, trusted_bias: int = 0) -> list:
    normalized = [_normalize_item(it) for it in items if it.get("url")]
    ranked = [_score_item(it, terms, trusted_bias)
              for it in normalized if not _is_noise_item(it)]
    ranked.sort(key=lambda x: (x.get("score", 0), x.get("ts", 0)), reverse=True)
    return _dedupe(ranked, cap)


def _sector_terms(sector: dict) -> list[str]:
    key = sector.get("key", "")
    terms = list(SECTOR_RELEVANCE_TERMS.get(key, []))
    terms += [sector.get("name", ""), key]
    for c in sector.get("constituents", [])[:12]:
        name = c.get("name", "").split(" (")[0]
        terms += [c.get("ticker", ""), name, name.split()[0] if name else ""]
    return [_norm(t) for t in terms if _norm(t)]


def _sector_relevant(it: dict, sector: dict) -> bool:
    raw_txt = " ".join([it.get("title", ""), it.get("summary", ""), it.get("source", "")])
    txt = _norm(raw_txt)
    title = _norm(it.get("title", ""))
    terms = _sector_terms(sector)
    constituent_hit = False
    for c in sector.get("constituents", [])[:20]:
        name = _norm(c.get("name", "").split(" (")[0])
        first = name.split()[0] if name else ""
        ticker = str(c.get("ticker", "")).strip()
        if (ticker and re.search(rf"\b{re.escape(ticker)}\b", raw_txt)) or \
           (name and name in txt) or (first and len(first) > 3 and re.search(rf"\b{re.escape(first)}\b", txt)):
            constituent_hit = True
            break
    if sector.get("key") != "crypto" and re.search(r"\bs p 500 target\b|\byear end s p 500\b", title):
        return False
    if sector.get("key") != "consumer" and "stock market today" in title:
        return constituent_hit
    if title.startswith("why your summer tomatoes cost"):
        return constituent_hit
    sector_hit = any((re.search(rf"\b{re.escape(t)}\b", txt) if len(t) <= 5 else t in txt)
                     for t in terms)
    if not sector_hit:
        return False
    anchor_terms = MARKET_ANCHOR_TERMS + tuple(SECTOR_ANCHOR_TERMS.get(sector.get("key", ""), ()))
    anchor_hit = any((re.search(rf"\b{re.escape(t)}\b", txt) if len(t) <= 5 else t in txt)
                     for t in anchor_terms)
    return anchor_hit or constituent_hit


def _sector_rank(items: list, sector: dict, cap: int) -> list:
    ranked = _rank(items, cap * 3, _sector_terms(sector))
    return [it for it in ranked if _sector_relevant(it, sector)][:cap]


def _targeted_source_news(query: str, geo: str, category: str, target_group: str,
                          terms: list[str], cap: int = 12, max_sites: int = 4) -> list:
    sites = settings.NEWS_SOURCE_TARGETS.get(target_group, [])
    if not sites:
        return []
    jobs = [(query, geo, category, site) for site in sites[:max_sites]]

    def one(job):
        q, g, cat, site = job
        qt = "official" if target_group == "OFFICIAL" else "trusted"
        return google_news(q, g, settings.NEWS_TRUSTED_PER_QUERY, category=cat,
                           site=site, query_type=qt)

    out = []
    try:
        with cf.ThreadPoolExecutor(max_workers=6) as ex:
            for items in ex.map(one, jobs):
                out += items
    except Exception as e:  # noqa: BLE001
        print(f"[news] trusted source pass failed '{query}': {e}")
    return _rank(out, cap, terms, trusted_bias=8)


def _load_previous() -> dict:
    try:
        if os.path.exists(settings.DATA_JSON_PATH):
            with open(settings.DATA_JSON_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"[news] previous payload unavailable: {e}")
    return {}


def _merge_news(old: list, new: list, cap: int, terms: list[str] = None) -> list:
    return _rank(_recent((old or []) + (new or [])), cap, terms)


def _latest_ts(items: list) -> int:
    return max((int(x.get("ts") or 0) for x in (items or [])), default=0)


def enrich(headlines: dict, sectors: list, telemetry: list) -> dict:
    previous = _load_previous()
    prev_wire = previous.get("news", [])
    prev_sector = previous.get("sector_news", {}) or {}
    prev_ticker = previous.get("ticker_news", {}) or {}

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
            wire += google_news(q[0], q[1], 3, query_type="index")

    # broad per-geo topic fan across the Economy/Tech/Markets/Crypto taxonomy — this is
    # the volume driver that lifts the wire to ~100 items per region (threaded).
    topic_jobs = [(q, geo, cat) for geo, lst in settings.WIRE_TOPICS.items()
                  for q, cat in lst]

    def _topic(job):
        q, geo, cat = job
        return google_news(q, geo, settings.NEWS_TOPIC_PER_QUERY, category=cat,
                           query_type="topic")

    try:
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for items in ex.map(_topic, topic_jobs):
                wire += items
    except Exception as e:  # noqa: BLE001
        print(f"[news] topic fan failed: {e}")

    # Trusted-source pass: compact targeted `site:` queries against high-signal sources.
    # This boosts quality without multiplying every ticker/sector query by every outlet.
    trusted_jobs = list(getattr(settings, "NEWS_SOURCE_QUERY_TOPICS", []))

    def _trusted(job):
        q, geo, cat, group = job
        max_sites = 7 if group == "ID" else 5
        return _targeted_source_news(q, geo, cat, group, q.split(), cap=10, max_sites=max_sites)

    try:
        with cf.ThreadPoolExecutor(max_workers=5) as ex:
            for items in ex.map(_trusted, trusted_jobs):
                wire += items
    except Exception as e:  # noqa: BLE001
        print(f"[news] trusted topic fan failed: {e}")

    wire += _from_curated(headlines)

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
        terms = [s["name"], s["key"]] + [c["ticker"] for c in s.get("constituents", [])[:8]]
        items = (google_news(usq, "US", 5, query_type="sector") +
                 google_news(idq, "ID", 5, query_type="sector"))
        items += _targeted_source_news(usq, "US", "MARKETS_FINANCE", "US", terms, cap=6, max_sites=2)
        items += _targeted_source_news(idq, "ID", "MARKETS_FINANCE", "ID", terms, cap=8, max_sites=5)
        items = _sector_rank(_recent(prev_sector.get(s["key"], []) + items), s, 14)   # ≤7d memory
        for it in items:
            it["sectors"] = [s["key"]]
        sector_news[s["key"]] = items[:8]
        wire += items[:5]

    # --- per-ticker news (gap/stale/priority budget; previous 7d memory is preserved) ---
    cons = []
    for s in sectors:
        for c in s["constituents"]:
            cons.append({"sector": s["key"], "ticker": c["ticker"],
                         "name": c["name"].split(" (")[0], "country": c["country"],
                         "tier": c.get("tier") or c.get("mktcap"),
                         "delta_pct": float(c.get("delta_pct") or 0.0)})

    now = _now()
    stale_s = getattr(settings, "NEWS_TICKER_STALE_HOURS", 72) * 3600

    def priority(c):
        existing = _recent(prev_ticker.get(c["ticker"], []))
        latest = _latest_ts(existing)
        gap = 1 if not existing else 0
        stale = 1 if latest and (now - latest) > stale_s else 0
        tier = {"mega": 35, "large": 25, "mid": 12, "small": 4}.get(c.get("tier"), 8)
        move = min(25, abs(c.get("delta_pct", 0.0)) * 8)
        return gap * 100 + stale * 55 + tier + move

    def fetch(t):
        tk, name, country = t["ticker"], t["name"], t["country"]
        if country == "CR":
            q = f"{name} {tk} crypto price regulation ETF"
            geo = "US"
        elif country == "ID":
            q = f"{tk} {name.split()[0]} saham emiten"
            geo = "ID"
        else:
            q = f"{tk} {name.split()[0]} stock earnings shares"
            geo = "US"
        terms = [tk, name.split()[0], name, t["sector"]]
        return tk, _rank(google_news(q, geo, 3, query_type="ticker"), 4, terms)

    selected = sorted(cons, key=priority, reverse=True)[:settings.NEWS_TICKER_QUERY_BUDGET]
    ticker_news = {tk: _recent(items, settings.NEWS_TICKER_KEEP_PER_TICKER)
                   for tk, items in prev_ticker.items()}
    try:
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for tk, items in ex.map(fetch, selected):
                merged = _merge_news(ticker_news.get(tk, []), items,
                                     settings.NEWS_TICKER_KEEP_PER_TICKER, [tk])
                if merged:
                    ticker_news[tk] = merged
    except Exception as e:  # noqa: BLE001
        print(f"[news] ticker fetch pool failed: {e}")

    # balance roughly 50/50 ID/US so neither region starves the wire
    fresh = _rank(_recent(prev_wire + wire), settings.NEWS_WIRE_CAP * 2)  # ≤7d memory
    half = settings.NEWS_WIRE_CAP // 2
    id_w = _dedupe([x for x in fresh if x.get("geo") == "ID"], half)
    us_w = _dedupe([x for x in fresh if x.get("geo") != "ID"], settings.NEWS_WIRE_CAP - half)
    wire = sorted(id_w + us_w, key=lambda x: (x.get("score", 0), x.get("ts", 0)), reverse=True)
    print(f"[news] wire={len(wire)} (≤7d · {len(id_w)} ID / {len(us_w)} US) · "
          f"sectors={len(sector_news)} · tickers_with_news={len(ticker_news)} · "
          f"ticker_queries={len(selected)}/{len(cons)}")
    return {"wire": wire, "sector_news": sector_news, "ticker_news": ticker_news}
