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
import sys

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings  # noqa: F401  (kept for parity / future tuning)

_SYSTEM = (
    "You are a cross-market macro analyst for an Indonesia-focused investor. "
    "Output RAW JSON only (no code fences), EXACTLY this schema: "
    '{"macro_analysis":[{"point":"one sentence explaining a key index/commodity/FX '
    'move or a macro update, include the number","refs":[{"t":"ticker","id":"<exact '
    'symbol from TELEMETRY>"}]}],'
    '"alerts":[{"title":"short alert headline","desc":"1-2 sentence description",'
    '"refs":[{"t":"news","i":0}]}]}. '
    "Provide 4-6 macro_analysis bullets and 3-5 alerts. EVERY item MUST include at "
    "least one ref, drawn ONLY from the provided data: ticker refs use an EXACT symbol "
    "from TELEMETRY; news/video refs use the given integer index ({\"t\":\"news\",\"i\":N} "
    "or {\"t\":\"video\",\"i\":N}). Never invent a source, symbol or index. Tie each "
    "point to what the numbers/headlines actually say. Plain text inside JSON values."
)


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


def _fallback(telemetry, sectors, tel_by_sym) -> dict:
    def ref(sym):
        r = tel_by_sym.get(sym)
        return [{"name": r["label"], "url": r["url"]}] if r else []

    ma = []
    for sym in ("^JKSE", "^GSPC", "^IXIC", "USDIDR=X", "GC=F", "BZ=F", "BTC-USD", "^TNX"):
        r = tel_by_sym.get(sym)
        if r:
            ma.append({"point": f"{r['label']} at {r['value']:,.2f}, {r['delta_pct']:+.2f}% on the session.",
                       "sources": ref(sym)})
        if len(ma) >= 5:
            break
    al = []
    for s in sorted(sectors, key=lambda s: abs(s.get("change", 0.0)), reverse=True)[:3]:
        cons = s.get("constituents") or []
        lead = cons[0] if cons else None
        srcs = [{"name": lead["ticker"], "url": lead["url"]}] if lead else []
        al.append({"title": f"{s['name']} {s['change']:+.2f}%",
                   "desc": (s.get("ai") or f"{s['name']} sector aggregate moved {s['change']:+.2f}%.")[:240],
                   "sources": srcs})
    return {"macro_analysis": ma, "alerts": al}


def compile_macro_alerts(telemetry, sectors, news, videos, signals="", summarize=None) -> dict:
    nlist, vlist = news[:14], videos[:8]
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
        obj = _parse_json(summarize(_SYSTEM, user))
        if obj:
            try:
                ma = []
                for it in (obj.get("macro_analysis") or [])[:6]:
                    pt = str(it.get("point", "")).strip()
                    if pt:
                        ma.append({"point": pt[:300],
                                   "sources": _resolve_refs(it.get("refs"), tel_by_sym, cons_by_tk, nlist, vlist)})
                al = []
                for it in (obj.get("alerts") or [])[:5]:
                    ti = str(it.get("title", "")).strip()
                    if ti:
                        al.append({"title": ti[:120],
                                   "desc": str(it.get("desc", "")).strip()[:240],
                                   "sources": _resolve_refs(it.get("refs"), tel_by_sym, cons_by_tk, nlist, vlist)})
                if ma or al:
                    result = {"macro_analysis": ma, "alerts": al}
            except Exception as e:  # noqa: BLE001
                print(f"[macro_alerts] mapping failed: {e}")
                result = None

    if result is None:
        print("[macro_alerts] deterministic fallback")
        result = _fallback(telemetry, sectors, tel_by_sym)
    print(f"[macro_alerts] {len(result['macro_analysis'])} macro bullets, "
          f"{len(result['alerts'])} alerts")
    return result
