"""Universal news link layer (PRD v2 · Module D3) + per-sector routing.

Takes the raw RSS headlines (which already carry a `link`) and produces a flat,
deduplicated news list where EVERY item has a verified source URL — items with
no extractable link are suppressed entirely, per the hard requirement. Each item
is tagged with a news category and routed to the sector keys it mentions.
"""
from __future__ import annotations

import re
import sys

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings

CATEGORY_KEYWORDS = {
    "MACRO":     ["rate", "inflation", "gdp", "policy", "central bank", "treasury",
                  "bi-rate", "the fed", "ecb", "rupiah", "fiscal", "tariff"],
    "STARTUP":   ["funding", "series ", "seed", "acquisition", "ipo", "venture",
                  "raises", "round", "startup", "valuation"],
    "PUBLIC_MKT":["earnings", "stock", "equity", "listed", "dividend", "buyback",
                  "guidance", "shares", "index", "bourse"],
    "CLIMATE":   ["renewable", "solar", "carbon", " ev", "energy", "climate",
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


def _sector_keys(text: str) -> list:
    t = text.lower()
    hits = []
    for sec in settings.SECTORS:
        toks = [sec["name"].lower(), sec["theme"].lower()]
        toks += [c[0].lower() for c in sec["constituents"]]          # tickers
        toks += [c[1].lower().split()[0] for c in sec["constituents"]]  # first word of name
        if any(re.search(r"\b" + re.escape(tok) + r"\b", t) for tok in toks if len(tok) > 3):
            hits.append(sec["key"])
    return hits


def route(headlines: dict, limit: int = 28) -> list:
    seen, items = set(), []
    for bucket in headlines.values():
        for h in bucket:
            url = (h.get("link") or "").strip()
            title = (h.get("title") or "").strip()
            if not url or not title:           # HARD REQUIREMENT: no URL → suppressed
                continue
            key = title.lower()[:80]
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "title": title,
                "source": h.get("source", ""),
                "url": url,
                "category": _category(title),
                "sectors": _sector_keys(title),
            })
    return items[:limit]
