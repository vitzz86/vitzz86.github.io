"""Polymarket prediction sentiment collector.

This is a read-only market-data layer for Project Cockpit. It uses public Gamma
API endpoints, filters out non-market noise, and returns compact sentiment cards
for the Intelligence Hub and Daily Brief. No wallet, auth, or trading is used.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
import time
from urllib.parse import urlencode

import requests

import sys
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings


CATEGORY_RULES = [
    ("fed_rates", "Fed & Rates", (
        "fed", "federal reserve", "interest rate", "rate cut", "rate hike", "inflation",
        "cpi", "pce", "jobs report", "unemployment", "treasury", "yield",
    )),
    ("macro", "Macro", (
        "recession", "gdp", "dollar", "dxy", "currency", "yen", "boj", "bank of japan",
        "ecb", "central bank", "tariff", "trade war",
    )),
    ("commodities", "Commodities", (
        "oil", "crude", "brent", "opec", "gold", "gas", "lng", "hormuz", "shipping",
        "commodity", "commodities",
    )),
    ("geopolitics", "Geopolitics", (
        "iran", "israel", "china", "taiwan", "russia", "ukraine", "war", "sanction",
        "geopolitical", "strait",
    )),
    ("crypto", "Crypto", (
        "bitcoin", "btc", "ethereum", "eth", "crypto", "stablecoin", "solana", "xrp",
        "coinbase", "binance", "etf",
    )),
    ("tech_ai", "Tech & AI", (
        "ai", "artificial intelligence", "nvidia", "openai", "semiconductor", "chip",
        "data center", "tesla", "microsoft",
    )),
    ("policy", "Policy", (
        "election", "congress", "senate", "white house", "regulation", "sec", "cftc",
        "tax", "debt ceiling",
    )),
]

NOISE_TERMS = (
    "nba", "nfl", "mlb", "nhl", "soccer", "football", "ufc", "boxing", "wimbledon",
    "world cup", "champions league", "grammys", "oscars", "emmys", "box office",
    "movie", "album", "song", "celebrity", "taylor swift", "love island", "chess",
    "youtube subscribers",
)


def _get(path: str, params: dict | None = None):
    url = settings.POLYMARKET_GAMMA_API.rstrip("/") + path
    try:
        r = requests.get(url, params=params or {}, timeout=12,
                         headers={"User-Agent": "ProjectCockpit/1.0"})
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001
        print(f"[polymarket] fetch failed {path}?{urlencode(params or {})}: {e}")
        return None


def _as_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, tuple):
        return list(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, list) else [parsed]
        except Exception:  # noqa: BLE001
            return [x.strip() for x in s.split(",") if x.strip()]
    return [v]


def _num(v, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(str(v).replace(",", ""))
    except Exception:  # noqa: BLE001
        return default


def _date_ts(v) -> int:
    if not v:
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).replace("Z", "+00:00")
    try:
        return int(dt.datetime.fromisoformat(s).timestamp())
    except Exception:  # noqa: BLE001
        return 0


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _text(event: dict, market: dict) -> str:
    parts = [
        event.get("title"), event.get("question"), event.get("description"),
        market.get("question"), market.get("title"), market.get("description"),
        " ".join(str(t.get("label") or t.get("name") or "") for t in event.get("tags") or [] if isinstance(t, dict)),
    ]
    return _norm(" ".join(str(x or "") for x in parts))


def _category(txt: str) -> tuple[str, str, int]:
    if any(term in txt for term in NOISE_TERMS):
        return "noise", "Noise", -100
    best = ("other", "Other", 0)
    for key, label, terms in CATEGORY_RULES:
        hits = sum(1 for term in terms if term in txt)
        if hits > best[2]:
            best = (key, label, hits)
    return best


def _volume(market: dict, event: dict, key: str) -> float:
    aliases = {
        "volume": ("volume", "volumeNum", "volumeClob", "volume_num"),
        "volume_24h": ("volume24hr", "volume_24hr", "volume24hrClob", "volume24h"),
        "liquidity": ("liquidity", "liquidityNum", "liquidityClob", "liquidity_num"),
    }[key]
    for obj in (market, event):
        for field in aliases:
            val = _num(obj.get(field), None)
            if val is not None and val > 0:
                return val
    return 0.0


def _outcomes(market: dict) -> tuple[list[str], list[float]]:
    outcomes = [str(x) for x in _as_list(market.get("outcomes"))]
    prices = [_num(x, 0.0) for x in _as_list(market.get("outcomePrices"))]
    if not outcomes or not prices or len(outcomes) != len(prices):
        return [], []
    return outcomes, prices


def _main_probability(outcomes: list[str], prices: list[float]) -> tuple[str, float]:
    if not outcomes:
        return "", 0.0
    yes_idx = next((i for i, x in enumerate(outcomes) if str(x).lower() == "yes"), None)
    idx = yes_idx if yes_idx is not None else max(range(len(prices)), key=lambda i: prices[i])
    return outcomes[idx], max(0.0, min(100.0, prices[idx] * 100.0))


def _url(event: dict, market: dict) -> str:
    slug = event.get("slug") or market.get("slug") or event.get("ticker") or market.get("ticker")
    if slug:
        return "https://polymarket.com/event/" + str(slug).strip("/")
    mid = market.get("id") or market.get("conditionId") or event.get("id")
    return "https://polymarket.com" + (f"/market/{mid}" if mid else "")


def _why(category: str, question: str, outcome: str, prob: float) -> str:
    q = question.rstrip("?")
    p = f"{prob:.0f}%"
    if category == "fed_rates":
        return f"Rate-path odds around {q} ({outcome} at {p}) matter for USD, yields, Nasdaq duration, and rupiah pressure."
    if category == "commodities":
        return f"Commodity odds around {q} ({outcome} at {p}) can feed oil, inflation, subsidy, and Indonesia resource-sector risk."
    if category == "crypto":
        return f"Crypto odds around {q} ({outcome} at {p}) help track digital-asset risk appetite before it reaches BTC and crypto equities."
    if category == "geopolitics":
        return f"Geopolitical odds around {q} ({outcome} at {p}) can reset risk appetite, oil expectations, and Asia FX sensitivity."
    if category == "tech_ai":
        return f"Tech and AI odds around {q} ({outcome} at {p}) add a forward-looking read on semiconductor and megacap leadership."
    if category == "macro":
        return f"Macro odds around {q} ({outcome} at {p}) are useful for checking whether markets are pricing growth, FX, or policy stress."
    return f"Prediction odds around {q} ({outcome} at {p}) add a forward-looking sentiment read alongside news and prices."


def _normalize_event(event: dict) -> list[dict]:
    markets = event.get("markets") if isinstance(event.get("markets"), list) else [event]
    out = []
    for market in markets:
        if not isinstance(market, dict):
            continue
        if market.get("closed") or market.get("archived") or event.get("closed") or event.get("archived"):
            continue
        txt = _text(event, market)
        cat, label, hits = _category(txt)
        if cat in ("noise", "other") or hits <= 0:
            continue
        outcomes, prices = _outcomes(market)
        outcome, prob = _main_probability(outcomes, prices)
        if prob <= 0:
            continue
        vol = _volume(market, event, "volume")
        vol24 = _volume(market, event, "volume_24h")
        liq = _volume(market, event, "liquidity")
        if vol < settings.POLYMARKET_MIN_VOLUME and liq < settings.POLYMARKET_MIN_LIQUIDITY:
            continue
        question = _clean(market.get("question") or event.get("title") or event.get("question"))
        if not question:
            continue
        end_date = market.get("endDate") or market.get("end_date") or event.get("endDate") or event.get("end_date")
        score = hits * 22 + math.log10(max(vol, 1)) * 7 + math.log10(max(liq, 1)) * 5
        if vol24:
            score += math.log10(max(vol24, 1)) * 8
        if cat in ("fed_rates", "commodities", "geopolitics", "crypto"):
            score += 12
        out.append({
            "id": str(market.get("id") or market.get("conditionId") or event.get("id") or question)[:120],
            "event_id": str(event.get("id") or ""),
            "market_id": str(market.get("id") or ""),
            "question": question,
            "event_title": _clean(event.get("title") or event.get("question") or question),
            "category": cat,
            "category_label": label,
            "outcome": outcome,
            "probability": round(prob, 1),
            "outcomes": outcomes[:8],
            "prices": [round(x * 100.0, 1) for x in prices[:8]],
            "volume": round(vol, 2),
            "volume_24h": round(vol24, 2),
            "liquidity": round(liq, 2),
            "end_date": str(end_date or ""),
            "end_ts": _date_ts(end_date),
            "url": _url(event, market),
            "score": round(score, 2),
            "why": _why(cat, question, outcome, prob),
        })
    return out


def _extract_events(obj) -> list[dict]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if not isinstance(obj, dict):
        return []
    events = []
    for key in ("events", "markets", "results", "data"):
        val = obj.get(key)
        if isinstance(val, list):
            events.extend(x for x in val if isinstance(x, dict))
    if not events and ("question" in obj or "markets" in obj):
        events.append(obj)
    return events


def _fetch_candidates() -> list[dict]:
    candidates = []
    for order in ("volume_24hr", "liquidity", "volume"):
        data = _get("/events", {
            "active": "true", "closed": "false", "order": order,
            "ascending": "false", "limit": settings.POLYMARKET_EVENT_LIMIT,
        })
        candidates.extend(_extract_events(data))
    for query in settings.POLYMARKET_QUERIES:
        data = _get("/public-search", {"query": query, "limit": settings.POLYMARKET_SEARCH_LIMIT})
        found = _extract_events(data)
        if not found:
            data = _get("/public-search", {"q": query, "limit": settings.POLYMARKET_SEARCH_LIMIT})
            found = _extract_events(data)
        candidates.extend(found)
    return candidates


def _dedupe(items: list[dict]) -> list[dict]:
    best = {}
    for item in items:
        key = item.get("market_id") or item.get("id") or item.get("url")
        if not key:
            continue
        prev = best.get(key)
        if prev is None or item.get("score", 0) > prev.get("score", 0):
            best[key] = item
    return list(best.values())


def _money(v: float) -> str:
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


def _implications(items: list[dict]) -> dict:
    if not items:
        return {
            "indonesia": "Indonesia: no high-confidence prediction-market signal passed the filter this run.",
            "us": "US / Global: no high-confidence prediction-market signal passed the filter this run.",
            "what_it_indicates": [],
        }
    top = items[:5]
    cats = []
    for item in top:
        label = item.get("category_label")
        if label and label not in cats:
            cats.append(label)
    lead = top[0]
    lead_line = f"{lead['outcome']} at {lead['probability']:.0f}% for \"{lead['question']}\""
    topic = ", ".join(cats[:3]).lower()
    indonesia = (
        f"Indonesia: prediction markets are centered on {topic}, with the top signal {lead_line}; "
        "watch the read-through to rupiah stability, foreign flows into JCI, oil sensitivity, and crypto beta."
    )
    us = (
        f"US / Global: prediction markets are centered on {topic}, with the top signal {lead_line}; "
        "treat it as a forward sentiment check against Fed expectations, megacap risk appetite, commodities, and geopolitics."
    )
    bullets = []
    for item in top[:4]:
        bullets.append(
            f"{item['category_label']}: {item['outcome']} priced at {item['probability']:.0f}% "
            f"on \"{item['question']}\" with {_money(item.get('liquidity') or item.get('volume') or 0)} liquidity/volume context."
        )
    return {"indonesia": indonesia, "us": us, "what_it_indicates": bullets}


def collect() -> dict:
    started = time.time()
    raw = _fetch_candidates()
    items = []
    for event in raw:
        items.extend(_normalize_event(event))
    items = sorted(_dedupe(items), key=lambda x: (x.get("score", 0), x.get("volume_24h", 0)), reverse=True)
    items = items[:settings.POLYMARKET_ITEM_LIMIT]
    summary = _implications(items)
    print(f"[polymarket] {len(items)} prediction signals ({time.time()-started:.1f}s)")
    return {
        "updated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Polymarket public Gamma API",
        "note": "Prediction markets are sentiment indicators, not facts or investment advice.",
        "indonesia_implication": summary["indonesia"],
        "global_implication": summary["us"],
        "what_it_indicates": summary["what_it_indicates"],
        "items": items,
        "health": {
            "candidate_count": len(raw),
            "item_count": len(items),
            "categories": {k: sum(1 for x in items if x.get("category") == k)
                           for k, _label, _terms in CATEGORY_RULES},
        },
    }
