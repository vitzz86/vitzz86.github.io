"""Macro Analysis + Active Alerts with grounded references.

One DeepSeek call turns telemetry + recent news + videos + sector moves into:
- macro_analysis: bullet points explaining index/commodity/FX moves & macro updates
- alerts: {title, description, sources}

References are GROUNDED to avoid hallucination: the model may only cite tickers
present in TELEMETRY (or a sector constituent), and news/videos by the integer
index we hand it. We resolve those back to the real Yahoo/CoinGecko article /
YouTube URLs; anything cited that isn't in the data is dropped. So every link is
real. A deterministic fallback keeps both panels populated (with real ticker
links) when no LLM key is configured.
"""
from __future__ import annotations

import json
import re
import sys

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings  # noqa: F401  (kept for parity / future tuning)

_SYSTEM = (
    "You are a cross-market macro strategist for an Indonesia-focused investor. "
    "Output RAW JSON only (no code fences), EXACTLY this schema: "
    '{"macro_analysis":[{"point":"2-3 connected sentences of cause-and-effect '
    'analysis","refs":[{"t":"ticker","id":"<exact TELEMETRY symbol>"},{"t":"news","i":0}]}],'
    '"alerts":[{"title":"short alert headline","desc":"1-2 sentence description",'
    '"refs":[{"t":"news","i":0}]}]}. '
    "MACRO_ANALYSIS: write 3-5 analytical bullets. Each bullet is 2-3 connected "
    "sentences that trace a CATALYST taken from the NEWS/VIDEOS provided through its "
    "cross-market consequences to the Indonesia implication (JCI / Rupiah / "
    "commodities / rates), the way a strategist reasons — not a price read-out. "
    "Synthesize from the actual headlines: explain WHY moves happened and what they "
    "mean for foreign flows, the Rupiah, commodity names, and duration-sensitive tech. "
    "Make the final bullet the key risk or linchpin to watch. "
    "ALERTS: 3-5 concrete, actionable alerts, each grounded in a specific headline or number. "
    "REFERENCES (mandatory, anti-hallucination): EVERY item includes >=1 ref drawn ONLY "
    "from the provided data — ticker refs use an EXACT symbol from TELEMETRY; news/video "
    'refs use the given integer index ({"t":"news","i":N} or {"t":"video","i":N}). Cite '
    "the NEWS/VIDEO that drove the point AND the ticker(s) it moved. Never invent a "
    "source, symbol or index. Plain text inside JSON values."
)


def _sentence_clip(text: str, limit: int) -> str:
    """Keep prose readable: never end a stored sentence mid-word or mid-thought."""
    txt = re.sub(r"\s+", " ", (text or "").strip())
    if len(txt) <= limit:
        return txt
    cut = txt[:limit].rstrip()
    # Prefer the last complete sentence inside the limit.
    m = list(re.finditer(r"[.!?](?:\s|$)", cut))
    if m and m[-1].end() >= max(120, int(limit * 0.55)):
        return cut[:m[-1].end()].strip()
    # Fallback: clean word boundary with ellipsis rather than a raw truncation.
    cut = cut.rsplit(" ", 1)[0].rstrip(" ,;:-")
    return cut + "..."


def _parse_json(raw: str) -> dict | None:
    txt = (raw or "").strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        txt = txt[txt.find("{"):]
    try:
        s, e = txt.index("{"), txt.rindex("}") + 1
        return json.loads(txt[s:e])
    except Exception:  # noqa: BLE001
        return None


def _resolve_refs(refs, tel_by_sym, cons_by_tk, news, videos) -> list:
    out, seen = [], set()
    for ref in (refs or []):
        if not isinstance(ref, dict):
            continue
        t = (ref.get("t") or ref.get("type") or "").lower()
        name = url = None
        if t in ("ticker", "index", "commodity", "fx"):
            sym = str(ref.get("id") or ref.get("sym") or ref.get("symbol") or "")
            r = tel_by_sym.get(sym) or cons_by_tk.get(sym)
            if r:
                name = r.get("label") or r.get("name") or r.get("ticker") or sym
                url = r.get("url")
        elif t == "news":
            i = ref.get("i")
            if isinstance(i, int) and 0 <= i < len(news):
                name = news[i].get("source") or "Source"
                url = news[i].get("url")
        elif t == "video":
            i = ref.get("i")
            if isinstance(i, int) and 0 <= i < len(videos):
                name = videos[i].get("channel") or "Video"
                url = videos[i].get("url")
        if url and url not in seen:
            seen.add(url)
            out.append({"name": (name or "Source")[:40], "url": url})
    return out


def _fallback(telemetry, sectors, tel_by_sym, news=None) -> dict:
    def ref(sym):
        r = tel_by_sym.get(sym)
        return [{"name": r["label"], "url": r["url"]}] if r else []

    ma = []
    for sym in ("^JKSE", "^GSPC", "^IXIC", "USDIDR=X", "GC=F", "BZ=F", "BTC-USD"):
        r = tel_by_sym.get(sym)
        if r:
            ma.append({"point": f"{r['label']} at {r['value']:,.2f}, {r['delta_pct']:+.2f}% on the session.",
                       "sources": ref(sym)})
        if len(ma) >= 4:
            break
    al = []
    # alerts from the freshest macro/markets headlines (real article links)
    for n in (news or [])[:3]:
        al.append({"title": n["title"][:120],
                   "desc": _sentence_clip(n.get("summary") or "", 420),
                   "sources": [{"name": n.get("source") or "Source", "url": n["url"]}]})
    # top up with the biggest sector moves if we have headroom
    for s in sorted(sectors, key=lambda s: abs(s.get("change", 0.0)), reverse=True):
        if len(al) >= 4:
            break
        cons = s.get("constituents") or []
        lead = cons[0] if cons else None
        al.append({"title": f"{s['name']} {s['change']:+.2f}%",
                   "desc": _sentence_clip(s.get("ai") or f"{s['name']} sector aggregate moved {s['change']:+.2f}%.", 420),
                   "sources": [{"name": lead["ticker"], "url": lead["url"]}] if lead else []})
    return {"macro_analysis": ma, "alerts": al}


def compile_macro_alerts(telemetry, sectors, news, videos, signals="", summarize=None) -> dict:
    nlist, vlist = news[:16], videos[:10]
    tel_by_sym = {r["symbol"]: r for r in telemetry}
    cons_by_tk = {c["ticker"]: c for s in sectors for c in s.get("constituents", [])}

    result = None
    if summarize:
        tstr = "\n".join(f"{r['symbol']} = {r['label']}: {r['value']} ({r['delta_pct']:+.2f}%)"
                         for r in telemetry)
        secstr = "; ".join(f"{s['name']} {s['change']:+.2f}%" for s in sectors)
        nstr = "\n".join(f"{i}. {n.get('source','')}: {n['title']}" for i, n in enumerate(nlist)) or "none"
        vstr = "\n".join(f"{i}. {v.get('channel','')}: {v['title']}" for i, v in enumerate(vlist)) or "none"
        user = (f"=== TELEMETRY (symbol = label: value (day%)) ===\n{tstr}\n\n"
                f"=== SECTORS ===\n{secstr}\n\n"
                f"=== NEWS (cite by index) ===\n{nstr}\n\n"
                f"=== VIDEOS (cite by index) ===\n{vstr}\n\n"
                f"=== FILTERED SIGNALS ===\n{signals or 'none'}")
        raw = summarize(_SYSTEM, user)
        obj = _parse_json(raw)
        if not obj:
            print(f"[macro_alerts] LLM unparseable (len={len(raw or '')}); tail: …{(raw or '')[-100:]!r}")
        if obj:
            try:
                ma = []
                for it in (obj.get("macro_analysis") or [])[:6]:
                    pt = str(it.get("point", "")).strip()
                    if pt:
                        ma.append({"point": _sentence_clip(pt, 700),
                                   "sources": _resolve_refs(it.get("refs"), tel_by_sym, cons_by_tk, nlist, vlist)})
                al = []
                for it in (obj.get("alerts") or [])[:5]:
                    ti = str(it.get("title", "")).strip()
                    if ti:
                        al.append({"title": ti[:120],
                                   "desc": _sentence_clip(str(it.get("desc", "")).strip(), 460),
                                   "sources": _resolve_refs(it.get("refs"), tel_by_sym, cons_by_tk, nlist, vlist)})
                if ma or al:
                    result = {"macro_analysis": ma, "alerts": al}
            except Exception as e:  # noqa: BLE001
                print(f"[macro_alerts] mapping failed: {e}")
                result = None

    if result is None:
        print("[macro_alerts] deterministic fallback")
        result = _fallback(telemetry, sectors, tel_by_sym, nlist)
    print(f"[macro_alerts] {len(result['macro_analysis'])} macro bullets, "
          f"{len(result['alerts'])} alerts")
    return result
