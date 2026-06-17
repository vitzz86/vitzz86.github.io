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
import json
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
    return {
        "sentiment": {"score": score, "label": label, "indonesia": idn,
                      "us": us, "global": glob, "crypto": cr},
        "synthesis": arbiter or "Synthesis pending the next scheduled window.",
        "key_themes": themes,
        "must_watch": [{"video": v, "why": (v.get("summary") or "")[:180]} for v in videos[:4]],
        "must_read": [{"news": n, "why": (n.get("summary") or n.get("source") or "")} for n in news[:4]],
        "news_digest": _regional_digest(news, "title", "geo"),
        "video_digest": _regional_digest(videos, "title", "geo"),
    }


DIGEST_TOPICS = (
    ("IHSG and Indonesian equities", ("ihsg", "jci", "saham", "emiten", "idx", "bei", "bursa")),
    ("rupiah and Bank Indonesia policy", ("rupiah", "bank indonesia", "bi-rate", "suku bunga", "idr")),
    ("US rates and Fed policy", ("federal reserve", "fed", "rate", "rates", "warsh", "treasury")),
    ("US indices and stock-market breadth", ("s&p", "s p 500", "nasdaq", "dow", "wall street")),
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


def _digest_topics(rows: list, title_key: str) -> list[str]:
    text = " ".join(str(x.get(title_key, "")) for x in rows).lower()
    scored = []
    for label, terms in DIGEST_TOPICS:
        hits = sum(1 for term in terms if term in text)
        if hits:
            scored.append((hits, label))
    scored.sort(reverse=True)
    return [label for _hits, label in scored[:4]]


def _regional_digest(items: list, title_key: str, geo_key: str) -> dict:
    def one(region: str) -> str:
        if region == "indonesia":
            rows = [x for x in items if x.get(geo_key) == "ID"]
            label = "Indonesia"
        else:
            rows = [x for x in items if x.get(geo_key) != "ID"]
            label = "US/global"
        topics = _digest_topics(rows[:12], title_key)
        if not rows:
            return f"{label}: no high-confidence items in the current 7-day window."
        if topics:
            return f"{label}: coverage focuses on {_human_list(topics)}."
        return f"{label}: coverage is concentrated in the latest market and business headlines."
    return {"indonesia": one("indonesia"), "us": one("us")}


def compile_brief(telemetry, sectors, news, videos, arbiter,
                  summarize=None, previous=None) -> dict:
    wk = _window_key()
    if (previous and previous.get("generated_for") == wk and previous.get("must_read")
            and previous.get("news_digest") and previous.get("video_digest")):
        print(f"[daily_brief] window {wk} unchanged — reusing cached brief")
        return previous

    brief = None
    if summarize:
        vlist, nlist = videos[:12], news[:14]
        vstr = "\n".join(f"{i}. [{v['category']}] {v['channel']}: {v['title']}"
                         for i, v in enumerate(vlist)) or "none"
        nstr = "\n".join(f"{i}. [{n.get('category','')}/{n.get('geo','')}] {n.get('source','')}: {n['title']}"
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
            "(by the given news index). score: 0=max bearish, 50=neutral, 100=max bullish. "
            "The news_digest and video_digest must summarize the full listed set by region: "
            "Indonesia in one complete sentence and US/global in one complete sentence each. "
            "Do not list headlines. Do not use semicolon-separated headline strings. "
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
                        mw.append({"video": vlist[i], "why": (it.get("why") or "").strip()})
                mr = []
                for it in (obj.get("must_read") or [])[:5]:
                    i = it.get("i")
                    if isinstance(i, int) and 0 <= i < len(nlist):
                        mr.append({"news": nlist[i], "why": (it.get("why") or "").strip()})
                if not mw:
                    mw = [{"video": v, "why": (v.get("summary") or "")[:160]} for v in videos[:4]]
                if not mr:
                    mr = [{"news": n, "why": (n.get("summary") or n.get("source") or "")} for n in news[:4]]
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
    nd_fallback = _regional_digest(news, "title", "geo")
    vd_fallback = _regional_digest(videos, "title", "geo")
    brief["news_digest"] = {
        "indonesia": ((brief.get("news_digest") or {}).get("indonesia") or nd_fallback["indonesia"]),
        "us": ((brief.get("news_digest") or {}).get("us") or nd_fallback["us"]),
    }
    brief["video_digest"] = {
        "indonesia": ((brief.get("video_digest") or {}).get("indonesia") or vd_fallback["indonesia"]),
        "us": ((brief.get("video_digest") or {}).get("us") or vd_fallback["us"]),
    }

    brief["generated_for"] = wk
    brief["generated_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[daily_brief] compiled for window {wk} "
          f"(sentiment {brief['sentiment']['score']}, "
          f"{len(brief['must_watch'])} watch / {len(brief['must_read'])} read)")
    return brief
