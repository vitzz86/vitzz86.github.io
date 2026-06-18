"""Intelligence Hub — Daily Brief agent.

Synthesizes accumulated news + videos + telemetry into a scheduled daily brief:
a market-sentiment score (with per-region breakdown), a synthesis paragraph,
must-watch videos, must-read news, and the day's key themes. Regenerates only at the
WIB windows in settings.DAILY_BRIEF_HOURS — cached between windows to bound DeepSeek
cost — and reuses the previous brief while the active window is unchanged. One LLM
call per regeneration; deterministic fallback keeps the panel populated with no key.
"""
from __future__ import annotations

import datetime as dt
import collections
import json
import re
import sys

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings
from tools import env_context


def _window_key(now: dt.datetime | None = None) -> str:
    now = now or env_context.now_wib()
    hours = sorted(settings.DAILY_BRIEF_HOURS)
    passed = [h for h in hours if now.hour >= h]
    if passed:
        return now.strftime("%Y-%m-%d") + f"T{max(passed):02d}"
    y = now - dt.timedelta(days=1)              # before first window → yesterday's last
    return y.strftime("%Y-%m-%d") + f"T{max(hours):02d}"


def _parse_json(raw: str) -> dict | None:
    txt = raw.strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        txt = txt[txt.find("{"):]
    try:
        s, e = txt.index("{"), txt.rindex("}") + 1
        return json.loads(txt[s:e])
    except Exception:  # noqa: BLE001
        return None


def _tel(telemetry: list, sym: str) -> float:
    for r in telemetry:
        if r.get("symbol") == sym:
            return r.get("delta_pct", 0.0)
    return 0.0


def _clamp(n) -> int:
    try:
        return max(0, min(100, int(round(float(n)))))
    except Exception:  # noqa: BLE001
        return 50


def _deterministic(telemetry, sectors, news, videos, arbiter) -> dict:
    aggs = [s.get("change", 0.0) for s in sectors]
    avg = sum(aggs) / len(aggs) if aggs else 0.0
    score = _clamp(50 + avg * 8)
    idn = _clamp(50 + _tel(telemetry, "^JKSE") * 10)
    us = _clamp(50 + ((_tel(telemetry, "^GSPC") + _tel(telemetry, "^IXIC")) / 2) * 10)
    cr = _clamp(50 + _tel(telemetry, "BTC-USD") * 5)
    glob = _clamp((idn + us) / 2)
    label = "Bullish" if score >= 60 else ("Bearish" if score <= 40 else "Neutral")
    themes = []
    for s in sorted(sectors, key=lambda s: abs(s.get("change", 0.0)), reverse=True)[:4]:
        ch = s.get("change", 0.0)
        tag = "BULLISH" if ch > 0.3 else ("BEARISH" if ch < -0.3 else "WATCH")
        themes.append({"title": s["name"], "tag": tag,
                       "text": (s.get("ai") or "; ".join(s.get("themes", [])[:1]))[:300]})
    videos = _rank_videos(videos)
    news = _rank_news(news)
    return _finalize_cards({
        "sentiment": {"score": score, "label": label, "indonesia": idn,
                      "us": us, "global": glob, "crypto": cr},
        "synthesis": arbiter or "Synthesis pending the next scheduled window.",
        "key_themes": themes,
        "must_watch": _balanced_watch_cards([], videos),
        "must_read": _balanced_read_cards([], news),
        "news_digest": _regional_digest(news, "title", "geo", telemetry),
        "video_digest": _regional_digest(videos, "title", "geo", telemetry),
    })


DIGEST_TOPICS = (
    ("IHSG and Indonesian equities", ("ihsg", "jci", "saham", "emiten", "idx", "bei", "bursa")),
    ("rupiah and Bank Indonesia policy", ("rupiah", "bank indonesia", "bi-rate", "suku bunga", "idr")),
    ("US rates and Fed policy", ("federal reserve", "fed", "rate", "rates", "warsh", "treasury")),
    ("US indices and stock-market breadth", ("s&p", "s p 500", "nasdaq", "dow", "wall street")),
    ("BOJ and Japan rate policy", ("boj", "bank of japan", "japan rate", "japanese rate", "naikkan suku bunga")),
    ("AI, semiconductors, and technology capex", ("ai", "artificial intelligence", "nvidia", "semiconductor", "chip", "data center")),
    ("commodities, energy, and shipping", ("oil", "gold", "nickel", "coal", "commodity", "commodities", "hormuz", "shipping")),
    ("crypto markets and regulation", ("bitcoin", "ethereum", "crypto", "kripto", "stablecoin", "blockchain")),
    ("company earnings, valuation, and corporate actions", ("earnings", "revenue", "profit", "valuation", "target", "ipo", "laba")),
    ("bonds, yields, and fixed income", ("bond", "bonds", "yield", "yields", "obligasi", "surat utang")),
    ("Asia policy and cross-market spillovers", ("boj", "japan", "nikkei", "china", "asia", "apac")),
    ("geopolitics and trade risk", ("iran", "tariff", "trade", "war", "geopolitical", "geopolitics")),
)


def _human_list(items: list[str]) -> str:
    items = [x for x in items if x]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


PROMO_REASON_PATTERNS = (
    r"https?://\S+",
    r"\b(referral|sign[- ]?up|promo code|use code|sponsor|sponsored|affiliate)\b.*",
    r"\b(subscribe|like and subscribe|join our|follow us|newsletter|discord|telegram|patreon)\b.*",
    r"\bnot financial advice\b.*",
    r"[╔╗╚╝═║╦╩╠╣]{3,}.*",
)
PROMO_REASON_TERMS = (
    "trade $", "get $", "referral", "subscribe", "sign-up", "signup",
    "promo code", "discord", "telegram", "patreon", "officially live in the united states",
    "watch this because", "read this because",
)
RATIONALE_TOPICS = (
    ("Indonesia flow is sensitive to Rupiah, Bank Indonesia, and IHSG direction, so this helps frame local risk appetite.",
     ("rupiah", "bank indonesia", "bi", "ihsg", "jci", "saham")),
    ("Rates remain the discount-rate anchor for equities, so this helps explain pressure on multiples, bonds, and the Rupiah.",
     ("fed", "federal reserve", "rates", "yield", "treasury", "warsh", "suku bunga")),
    ("AI and semiconductor capex are still leading the tech cycle, making this useful for tracking market leadership.",
     ("ai", "artificial intelligence", "nvidia", "semiconductor", "chip", "data center")),
    ("Energy and commodity moves feed inflation expectations and Indonesia's resource exposure, so this is worth watching.",
     ("oil", "brent", "gold", "nickel", "coal", "commodity", "hormuz", "shipping")),
    ("Digital-asset sentiment can turn quickly around Bitcoin, stablecoins, and regulation, so this keeps crypto risk in view.",
     ("bitcoin", "btc", "ethereum", "crypto", "stablecoin", "token", "kalshi", "strategy")),
    ("Japan and BOJ policy can spill into Asian yields and FX, making this relevant for regional positioning.",
     ("boj", "bank of japan", "japan", "nikkei")),
    ("Earnings and corporate actions reveal whether the market move is broadening or staying concentrated in a few names.",
     ("earnings", "revenue", "profit", "stock movers", "shares", "ipo", "m&a", "merger", "acquisition")),
    ("Geopolitical and trade headlines can quickly reset risk appetite, oil expectations, and defensive positioning.",
     ("iran", "tariff", "trade war", "geopolitical", "war")),
)


def _plain_text(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", str(s or ""))
    for pat in PROMO_REASON_PATTERNS:
        s = re.sub(pat, " ", s, flags=re.I)
    s = re.sub(r"[\[\]{}<>|*_`~]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" -:;,.")
    return s


def _one_sentence(s: str, max_len: int = 210) -> str:
    s = _plain_text(s)
    if not s:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", s)
    sent = next((p.strip() for p in parts if len(p.strip()) >= 35), parts[0].strip())
    sent = re.sub(r"\s+", " ", sent).strip(" -:;,.")
    if len(sent) > max_len:
        sent = sent[:max_len].rsplit(" ", 1)[0].strip(" -:;,.")
    return sent + ("." if sent and sent[-1] not in ".!?" else "")


def _is_noisy_reason(s: str) -> bool:
    t = s.lower()
    if len(s.strip()) < 35:
        return True
    if any(term in t for term in PROMO_REASON_TERMS):
        return True
    return bool(re.search(r"https?://|[╔╗╚╝═║╦╩╠╣]{3,}", s))


def _term_match(text: str, term: str) -> bool:
    term = str(term or "").lower().strip()
    if not term:
        return False
    text = str(text or "").lower()
    if re.fullmatch(r"[a-z0-9]+", term):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text))
    return term in text


def _topic_score(text: str, phrase: str, terms: tuple[str, ...], item: dict) -> int:
    hits = sum(1 for term in terms if _term_match(text, term))
    if not hits:
        return 0
    score = hits * 10
    category = item.get("category")
    geo = item.get("geo")
    if category == "crypto" or category == "CRYPTO":
        if phrase.startswith("Digital-asset"):
            score += 30
    if category == "market_id" or geo == "ID":
        if phrase.startswith("Indonesia flow"):
            score += 20
    if category == "market_us" and (
        phrase.startswith("Rates") or phrase.startswith("Earnings") or
        phrase.startswith("Geopolitical") or phrase.startswith("AI") or
        phrase.startswith("Energy") or phrase.startswith("Japan")
    ):
        score += 6
    if phrase.startswith("Japan"):
        score += 25
    return score


def _fallback_reason(item: dict, kind: str) -> str:
    txt = " ".join(str(item.get(k, "")) for k in ("title", "summary", "source", "channel")).lower()
    scored = [(_topic_score(txt, phrase, terms, item), phrase) for phrase, terms in RATIONALE_TOPICS]
    scored = [(score, phrase) for score, phrase in scored if score]
    if scored:
        return max(scored, key=lambda x: x[0])[1]
    return "This is a fresh high-priority item in today's market intelligence flow, useful for catching changes before they spread."


def _clean_why(raw: str, item: dict, kind: str) -> str:
    why = _one_sentence(raw)
    if _is_noisy_reason(why):
        why = _fallback_reason(item, kind)
    return _one_sentence(why, 220)


def _video_score(v: dict) -> int:
    txt = " ".join(str(v.get(k, "")) for k in ("title", "summary", "channel")).lower()
    score = int(v.get("score") or 0)
    score += {"market_id": 30, "market_us": 28, "crypto": 12}.get(v.get("category"), 10)
    for phrase, terms in RATIONALE_TOPICS:
        if _topic_score(txt, phrase, terms, v):
            score += 14
    if any(_term_match(txt, term) for term in PROMO_REASON_TERMS):
        score -= 35
    if re.search(r"\b(beginners?|how to trade|perps?|referral|sign[- ]?up)\b", txt):
        score -= 20
    return score


def _promo_video(v: dict) -> bool:
    txt = " ".join(str(v.get(k, "")) for k in ("title", "summary", "channel")).lower()
    return any(_term_match(txt, term) for term in PROMO_REASON_TERMS) or bool(
        re.search(r"\b(beginners?|how to trade|referral|sign[- ]?up|subscribe)\b", txt))


def _rank_videos(videos: list) -> list:
    return sorted(videos or [], key=lambda v: (_video_score(v), int(v.get("ts") or 0)), reverse=True)


def _rank_news(news: list) -> list:
    return sorted(news or [], key=lambda n: (int(n.get("score") or 0), int(n.get("ts") or 0)), reverse=True)


def _dedupe_cards(cards: list, key_fn) -> list:
    seen, out = set(), []
    for card in cards:
        key = key_fn(card)
        if key and key not in seen:
            seen.add(key)
            out.append(card)
    return out


def _balanced_watch_cards(existing: list, videos: list, size: int = 4) -> list:
    ranked = [v for v in _rank_videos(videos) if not _promo_video(v)]
    card_by_id = {((m.get("video") or {}).get("video_id")): m for m in (existing or [])}
    result = []
    used_ids = set()

    def pick(cat: str):
        for v in ranked:
            if v.get("category") == cat and v.get("video_id") not in used_ids:
                return card_by_id.get(v.get("video_id")) or {"video": v, "why": _fallback_reason(v, "video")}
        return None

    for cat in ("market_id", "market_us", "crypto", "market_us"):
        card = pick(cat)
        if card:
            used_ids.add((card.get("video") or {}).get("video_id"))
            result.append(card)
    for v in ranked:
        if len(result) >= size:
            break
        vid = v.get("video_id")
        if vid not in used_ids:
            used_ids.add(vid)
            result.append(card_by_id.get(vid) or {"video": v, "why": _fallback_reason(v, "video")})
    return _dedupe_cards(result, lambda m: (m.get("video") or {}).get("video_id"))[:size]


def _balanced_read_cards(existing: list, news: list, size: int = 4) -> list:
    ranked = _rank_news(news)
    card_by_url = {((m.get("news") or {}).get("url")): m for m in (existing or [])}
    result = []

    def used_urls():
        return {((m.get("news") or {}).get("url")) for m in result}

    def pick(fn):
        sources = {((m.get("news") or {}).get("source")) for m in result}
        for n in ranked:
            if n.get("url") in used_urls():
                continue
            if fn(n) and (len(result) < 2 or n.get("source") not in sources):
                return card_by_url.get(n.get("url")) or {"news": n, "why": _fallback_reason(n, "news")}
        return None

    for fn in (
        lambda n: n.get("geo") == "ID",
        lambda n: n.get("geo") != "ID",
        lambda n: n.get("category") in {"MARKETS_FINANCE", "TECH"},
        lambda n: n.get("category") == "CRYPTO",
    ):
        card = pick(fn)
        if card:
            result.append(card)
    for n in ranked:
        if len(result) >= size:
            break
        if n.get("url") not in used_urls():
            result.append(card_by_url.get(n.get("url")) or {"news": n, "why": _fallback_reason(n, "news")})
    return _dedupe_cards(result, lambda m: (m.get("news") or {}).get("url"))[:size]


def _finalize_cards(brief: dict) -> dict:
    for m in brief.get("must_watch") or []:
        v = m.get("video") or {}
        m["why"] = _clean_why(m.get("why") or v.get("summary") or "", v, "video")
    for m in brief.get("must_read") or []:
        n = m.get("news") or {}
        m["why"] = _clean_why(m.get("why") or n.get("summary") or "", n, "news")
    brief["quality_audit"] = _brief_quality(brief)
    return brief


def _brief_quality(brief: dict) -> dict:
    watch = brief.get("must_watch") or []
    read = brief.get("must_read") or []
    noisy = sum(1 for m in watch + read if _is_noisy_reason(_one_sentence(m.get("why") or "")))
    return {
        "must_watch_count": len(watch),
        "must_read_count": len(read),
        "noisy_reason_count": noisy,
        "watch_categories": dict(collections.Counter((m.get("video") or {}).get("category") or "UNKNOWN" for m in watch)),
        "read_geo": dict(collections.Counter((m.get("news") or {}).get("geo") or "UNKNOWN" for m in read)),
        "read_categories": dict(collections.Counter((m.get("news") or {}).get("category") or "UNKNOWN" for m in read)),
        "duplicate_read_sources": max(0, len(read) - len({(m.get("news") or {}).get("source") for m in read})),
    }


def _brief_has_noisy_reasons(brief: dict) -> bool:
    for m in (brief.get("must_watch") or []) + (brief.get("must_read") or []):
        if _is_noisy_reason(_one_sentence(m.get("why") or "")):
            return True
    return False


def _telemetry_row(telemetry: list | None, sym: str) -> dict | None:
    for r in telemetry or []:
        if r.get("symbol") == sym:
            return r
    return None


def _fmt_pct(n) -> str:
    try:
        v = float(n)
        return f"{v:+.2f}%"
    except Exception:  # noqa: BLE001
        return ""


def _indicator(label: str, row: dict | None, note: str = "") -> str:
    if not row:
        return ""
    pct = _fmt_pct(row.get("delta_pct"))
    return f"{label} {pct}{note}" if pct else ""


def _tone(score: float) -> str:
    if score >= 1.0:
        return "bullish"
    if score <= -1.0:
        return "bearish"
    return "mixed"


def _regional_indicators(telemetry: list | None, region: str, topics: list[str]) -> tuple[str, list[str]]:
    if region == "indonesia":
        jci = _telemetry_row(telemetry, "^JKSE")
        usdidr = _telemetry_row(telemetry, "USDIDR=X")
        btc = _telemetry_row(telemetry, "BTC-USD")
        score = 0
        if jci:
            score += 1 if float(jci.get("delta_pct") or 0) > 0 else -1 if float(jci.get("delta_pct") or 0) < 0 else 0
        if usdidr:
            fx = float(usdidr.get("delta_pct") or 0)
            score += -1 if fx > 0 else 1 if fx < 0 else 0
        fx_note = ""
        if usdidr:
            fx_note = " (rupiah weaker)" if float(usdidr.get("delta_pct") or 0) > 0 else " (rupiah stronger)" if float(usdidr.get("delta_pct") or 0) < 0 else ""
        indicators = [_indicator("JCI", jci), _indicator("USD/IDR", usdidr, fx_note)]
        if any("crypto" in t.lower() for t in topics):
            indicators.append(_indicator("BTC", btc))
        return _tone(score), [x for x in indicators if x][:4]

    spx = _telemetry_row(telemetry, "^GSPC")
    ndx = _telemetry_row(telemetry, "^IXIC")
    dow = _telemetry_row(telemetry, "^DJI")
    tnx = _telemetry_row(telemetry, "^TNX")
    dxy = _telemetry_row(telemetry, "DX-Y.NYB")
    brent = _telemetry_row(telemetry, "BZ=F")
    gold = _telemetry_row(telemetry, "GC=F")
    btc = _telemetry_row(telemetry, "BTC-USD")
    equity_rows = [x for x in (spx, ndx, dow) if x]
    score = sum(1 if float(x.get("delta_pct") or 0) > 0 else -1 if float(x.get("delta_pct") or 0) < 0 else 0
                for x in equity_rows)
    indicators = [_indicator("S&P 500", spx), _indicator("Nasdaq", ndx)]
    topic_text = " ".join(topics).lower()
    if "rates" in topic_text or "fed" in topic_text or "bonds" in topic_text:
        indicators.append(_indicator("US 10Y", tnx))
    if "commodities" in topic_text or "oil" in topic_text or "shipping" in topic_text:
        indicators.append(_indicator("Brent", brent))
    if "gold" in topic_text:
        indicators.append(_indicator("Gold", gold))
    if "crypto" in topic_text:
        indicators.append(_indicator("BTC", btc))
    if len([x for x in indicators if x]) < 3:
        indicators.append(_indicator("DXY", dxy))
    return _tone(score), [x for x in indicators if x][:4]


def _item_text(it: dict, title_key: str) -> str:
    return " ".join(str(it.get(k, "")) for k in (title_key, "summary", "source", "channel")).lower()


def _topic_label(label: str, rows: list, title_key: str) -> str:
    text = " ".join(_item_text(x, title_key) for x in rows)
    if label == "BOJ and Japan rate policy":
        pct = re.search(r"\b\d+(?:\.\d+)?\s*%", text)
        return f"BOJ rate-policy coverage around {pct.group(0)}" if pct else "BOJ and Japan rate policy"
    if label == "rupiah and Bank Indonesia policy" and re.search(r"\b17[,.]\d{3}\b", text):
        return "rupiah pressure and Bank Indonesia policy"
    if label == "commodities, energy, and shipping" and "hormuz" in text:
        return "oil, shipping, and Strait of Hormuz risk"
    return label


def _digest_topics(rows: list, title_key: str) -> list[str]:
    scored = []
    for label, terms in DIGEST_TOPICS:
        row_hits = sum(1 for row in rows if any(_term_match(_item_text(row, title_key), term) for term in terms))
        term_hits = sum(1 for row in rows for term in terms if _term_match(_item_text(row, title_key), term))
        if row_hits:
            scored.append((row_hits, term_hits, _topic_label(label, rows, title_key)))
    scored.sort(reverse=True)
    recurring = [label for hits, _term_hits, label in scored if hits >= 2]
    return (recurring or [label for _hits, _term_hits, label in scored])[:5]


def _regional_digest(items: list, title_key: str, geo_key: str, telemetry: list | None = None) -> dict:
    def one(region: str) -> str:
        if region == "indonesia":
            rows = [x for x in items if x.get(geo_key) == "ID"]
            label = "Indonesia"
        else:
            rows = [x for x in items if x.get(geo_key) != "ID"]
            label = "US/global"
        topics = _digest_topics(rows[:16], title_key)
        if not rows:
            return f"{label}: no high-confidence items in the current 7-day window."
        tone, indicators = _regional_indicators(telemetry, region, topics)
        prefix = f"{label}: {tone} tone"
        if indicators:
            prefix += f" with {_human_list(indicators)}"
        if topics:
            return f"{prefix}; coverage focuses on {_human_list(topics)}."
        return f"{prefix}; coverage is concentrated in the latest market and business headlines."
    return {"indonesia": one("indonesia"), "us": one("us")}


def compile_brief(telemetry, sectors, news, videos, arbiter,
                  summarize=None, previous=None) -> dict:
    wk = _window_key()
    if (previous and previous.get("generated_for") == wk and previous.get("must_read")
            and previous.get("news_digest") and previous.get("video_digest")
            and not _brief_has_noisy_reasons(previous)):
        print(f"[daily_brief] window {wk} unchanged — reusing cached brief")
        return _finalize_cards(previous)

    brief = None
    videos = _rank_videos(videos)
    news = _rank_news(news)
    if summarize:
        vlist, nlist = videos[:12], news[:14]
        def snippet(x):
            return _one_sentence(x.get("summary") or x.get("title") or "", 260)
        vstr = "\n".join(f"{i}. [{v['category']}/{v.get('geo','')}] {v['channel']}: {v['title']} — {snippet(v)}"
                         for i, v in enumerate(vlist)) or "none"
        nstr = "\n".join(f"{i}. [{n.get('category','')}/{n.get('geo','')}] {n.get('source','')}: {n['title']} — {snippet(n)}"
                         for i, n in enumerate(nlist)) or "none"
        tstr = "\n".join(f"{r['label']}: {r['value']} ({r['delta_pct']:+.2f}%)" for r in telemetry)
        secstr = "; ".join(f"{s['name']} {s['change']:+.2f}%" for s in sectors)
        raw = summarize(
            "You are the chief intelligence officer for an Indonesia-focused investor. "
            "Output RAW JSON only (no code fences), EXACTLY this schema: "
            '{"sentiment":{"score":int 0-100,"label":"2-3 words","indonesia":int,"us":int,'
            '"global":int,"crypto":int},'
            '"synthesis":"100-150 word paragraph on today\'s cross-market picture, Indonesia lens",'
            '"news_digest":{"indonesia":"1 sentence","us":"1 sentence"},'
            '"video_digest":{"indonesia":"1 sentence","us":"1 sentence"},'
            '"key_themes":[{"title":"short","tag":"BULLISH|BEARISH|WATCH","text":"1-2 sentences"}],'
            '"must_watch":[{"i":video_index,"why":"1 sentence"}],'
            '"must_read":[{"i":news_index,"why":"1 sentence"}]}. '
            "Provide 3-5 key_themes, 3-5 must_watch (by the given video index), 3-5 must_read "
            "(by the given news index). Every must_watch.why and must_read.why must be exactly one useful sentence "
            "explaining why it matters for markets or the user's portfolio; never repeat sponsor copy, referral links, "
            "subscribe prompts, generic channel descriptions, or raw source names. score: 0=max bearish, 50=neutral, 100=max bullish. "
            "The news_digest and video_digest must summarize the full listed set by region: "
            "Indonesia in one complete sentence and US/global in one complete sentence each. "
            "Each sentence must start with a tone label (bullish, bearish, or mixed), include 2-4 key indicators "
            "from telemetry with up/down percentages when relevant, then name 3-5 recurring topics or concrete events "
            "that appear across multiple items, using title plus summary/description, not title alone. Include specific "
            "catalysts and numbers when present, for example BOJ rate-hike coverage around 1%, Rupiah near 17,780, "
            "Fed hold, Hormuz reopening, oil moves, or S&P/Nasdaq moves. Do not list headlines. "
            "Do not use semicolon-separated headline strings. "
            "Describe the common topics and market implications in plain language. "
            "Indices are given as % day moves. Plain text inside JSON values, no markdown.",
            f"=== TELEMETRY ===\n{tstr}\n\n=== SECTORS ===\n{secstr}\n\n"
            f"=== VIDEOS (pick must_watch by index) ===\n{vstr}\n\n"
            f"=== NEWS (pick must_read by index) ===\n{nstr}")
        obj = _parse_json(raw) if raw else None
        if obj:
            try:
                mw = []
                for it in (obj.get("must_watch") or [])[:5]:
                    i = it.get("i")
                    if isinstance(i, int) and 0 <= i < len(vlist):
                        mw.append({"video": vlist[i], "why": _clean_why(it.get("why") or "", vlist[i], "video")})
                mr = []
                for it in (obj.get("must_read") or [])[:5]:
                    i = it.get("i")
                    if isinstance(i, int) and 0 <= i < len(nlist):
                        mr.append({"news": nlist[i], "why": _clean_why(it.get("why") or "", nlist[i], "news")})
                if not mw:
                    mw = _balanced_watch_cards([], videos)
                if not mr:
                    mr = _balanced_read_cards([], news)
                mw = _balanced_watch_cards(mw, videos)
                mr = _balanced_read_cards(mr, news)
                sent = obj.get("sentiment") or {}
                brief = {
                    "sentiment": {
                        "score": _clamp(sent.get("score", 50)),
                        "label": str(sent.get("label", "Neutral"))[:40],
                        "indonesia": _clamp(sent.get("indonesia", 50)),
                        "us": _clamp(sent.get("us", 50)),
                        "global": _clamp(sent.get("global", 50)),
                        "crypto": _clamp(sent.get("crypto", 50)),
                    },
                    "synthesis": str(obj.get("synthesis", "")).strip(),
                    "news_digest": {
                        "indonesia": str((obj.get("news_digest") or {}).get("indonesia", "")).strip()[:260],
                        "us": str((obj.get("news_digest") or {}).get("us", "")).strip()[:260],
                    },
                    "video_digest": {
                        "indonesia": str((obj.get("video_digest") or {}).get("indonesia", "")).strip()[:260],
                        "us": str((obj.get("video_digest") or {}).get("us", "")).strip()[:260],
                    },
                    "key_themes": [{"title": str(t.get("title", ""))[:60],
                                    "tag": str(t.get("tag", "WATCH")).upper(),
                                    "text": str(t.get("text", ""))[:300]}
                                   for t in (obj.get("key_themes") or [])[:5]],
                    "must_watch": mw, "must_read": mr,
                }
            except Exception as e:  # noqa: BLE001
                print(f"[daily_brief] mapping failed: {e}")
                brief = None

    if brief is None:
        print("[daily_brief] deterministic fallback")
        brief = _deterministic(telemetry, sectors, news, videos, arbiter)
    nd_fallback = _regional_digest(news, "title", "geo", telemetry)
    vd_fallback = _regional_digest(videos, "title", "geo", telemetry)
    brief["news_digest"] = {
        "indonesia": ((brief.get("news_digest") or {}).get("indonesia") or nd_fallback["indonesia"]),
        "us": ((brief.get("news_digest") or {}).get("us") or nd_fallback["us"]),
    }
    brief["video_digest"] = {
        "indonesia": ((brief.get("video_digest") or {}).get("indonesia") or vd_fallback["indonesia"]),
        "us": ((brief.get("video_digest") or {}).get("us") or vd_fallback["us"]),
    }
    brief = _finalize_cards(brief)

    brief["generated_for"] = wk
    brief["generated_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[daily_brief] compiled for window {wk} "
          f"(sentiment {brief['sentiment']['score']}, "
          f"{len(brief['must_watch'])} watch / {len(brief['must_read'])} read)")
    return brief
