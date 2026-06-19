"""Project Cockpit — master orchestration script.

Runs the four-agent pipeline (Quant -> OSINT Hunter -> Cross-Market Arbiter ->
Chief of Staff) as a stateful graph and compiles the strict data.json contract
consumed by cockpit.html.

LLM base: DeepSeek (native API or OpenRouter, picked from env). When no key is
configured the pipeline still completes through deterministic fallbacks, so a
fresh clone produces a valid dashboard at $0.

Guardrails (PRD §8): any failure leaves the existing data.json untouched and
logs the diagnostic; schema violations halt the run before the write.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from config import settings                      # noqa: E402
from templates import prompt_templates as pt     # noqa: E402
from tools import (daily_brief, enterprise_osint, env_context,  # noqa: E402
                   macro_alerts, market_telemetry, news_router, podcasts,
                   sectors, spotify, trending, universe, videos)


# ---------------------------------------------------------------- LLM access
def call_deepseek(system: str, user: str) -> str | None:
    """One DeepSeek chat completion. Returns None when unavailable/failed."""
    import requests

    if settings.DEEPSEEK_API_KEY:
        url, model = settings.DEEPSEEK_NATIVE_URL, settings.DEEPSEEK_NATIVE_MODEL
        headers = {"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"}
    elif settings.OPENROUTER_API_KEY:
        url, model = settings.OPENROUTER_URL, settings.OPENROUTER_MODEL
        headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                   "HTTP-Referer": "https://vitosamudra.com",
                   "X-Title": "Project Cockpit"}
    else:
        print("[llm] no DeepSeek/OpenRouter key configured — using fallback route")
        return None
    import time
    payload = {"model": model,
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": user}],
               "temperature": 0.4, "max_tokens": settings.LLM_MAX_TOKENS}
    for attempt in range(3):                       # retry transient rate-limits/timeouts
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=settings.LLM_TIMEOUT_S)
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:  # noqa: BLE001
            print(f"[llm] DeepSeek call failed (attempt {attempt+1}): {e}")
            time.sleep(1.5)
    return None


# ---------------------------------------------------------------- graph nodes
def node_quant(state: dict) -> dict:
    tel = market_telemetry.collect()
    print(f"[quant] {len(tel['rows'])} tickers, anomaly={tel['anomaly']}")
    return {"telemetry": tel["rows"], "anomaly": tel["anomaly"],
            "anomaly_desc": tel["anomaly_desc"]}


def _tel_value(r: dict) -> str:
    val = float(r.get("value") or 0.0)
    return f"{val:,.3f}%" if r.get("value_unit") == "percent" else f"{val:,.2f}"


def _tel_move(r: dict) -> str:
    mv = float(r.get("delta_pct") or 0.0)
    if r.get("delta_unit") == "bp":
        return f"{mv:+.1f} bp"
    return f"{mv:+.2f}%"


def _tel_line(r: dict) -> str:
    return f"{r['label']}: {_tel_value(r)} ({_tel_move(r)})"


def _coverage_universe_summary(sectors_list: list) -> dict:
    return universe.coverage_summary(sectors_list)


def node_hunter(state: dict) -> dict:
    headlines = enterprise_osint.scan_feeds()
    if state["anomaly"]:
        print(f"[hunter] anomaly override -> Tavily: {state['anomaly_desc']}")
        headlines["anomaly_hunt"] = enterprise_osint.tavily_hunt(state["anomaly_desc"])
    flat = "\n".join(f"{cat}: {h['source']} — {h['title']}"
                     for cat, items in headlines.items() for h in items)
    filtered = call_deepseek(
        pt.HUNTER_PERSONA,
        pt.HUNTER_TASK.format(
            anomaly=state["anomaly_desc"] or "none — standard structural scan",
            headlines=flat or "no feeds reachable"))
    print(f"[hunter] {sum(len(v) for v in headlines.values())} headlines kept")
    return {"headlines": headlines, "signals": filtered or flat}


def node_arbiter(state: dict) -> dict:
    tel_str = "\n".join(_tel_line(r) for r in state["telemetry"])
    brief = call_deepseek(
        pt.ARBITER_PERSONA,
        pt.ARBITER_TASK.format(telemetry=tel_str or "unavailable",
                               signals=state["signals"] or "unavailable"))
    print(f"[arbiter] brief={'llm' if brief else 'fallback pending'}")
    return {"arbiter": brief or ""}


def node_chief(state: dict) -> dict:
    tel_str = "\n".join(_tel_line(r) for r in state["telemetry"])
    raw = call_deepseek(
        pt.CHIEF_PERSONA,
        pt.CHIEF_TASK.replace("{telemetry}", tel_str or "unavailable")
                     .replace("{anomaly}", state["anomaly_desc"] or "none")
                     .replace("{headlines}", state["signals"] or "unavailable")
                     .replace("{arbiter}", state["arbiter"] or "unavailable"))
    parsed = _parse_chief_json(raw) if raw else None
    if parsed is None:
        print("[chief] using deterministic fallback composition")
        parsed = _fallback_quadrants(state)
    return {"compiled": parsed}


def _parse_chief_json(raw: str) -> dict | None:
    txt = raw.strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        txt = txt[txt.find("{"):]
    try:
        start, end = txt.index("{"), txt.rindex("}") + 1
        obj = json.loads(txt[start:end])
        for key, n in (("market", 1), ("economic", 1), ("tech_ai", 1),
                       ("political", 1), ("executive_brief", 3)):
            if not isinstance(obj.get(key), list) or len(obj[key]) < n:
                raise ValueError(f"chief contract violated on '{key}'")
        if not isinstance(obj.get("arbiter_brief"), str) or not obj["arbiter_brief"]:
            raise ValueError("chief contract violated on 'arbiter_brief'")
        return obj
    except Exception as e:  # noqa: BLE001
        print(f"[chief] JSON contract parse failed: {e}")
        return None


def _fallback_quadrants(state: dict) -> dict:
    """Deterministic compile path when the LLM is unreachable."""
    def pick(cat: str, n: int, tag: str) -> list:
        items = state["headlines"].get(cat, [])[:n]
        return [f"{h['title']} ({h['source']})" for h in items] or \
               [f"{tag} wires quiet this cycle — no structural signals parsed."]

    tel = {r["symbol"]: r for r in state["telemetry"]}
    market = []
    if "^JKSE" in tel:
        r = tel["^JKSE"]
        market.append(f"JCI closed at {r['value']:,.0f} ({r['delta_pct']:+.2f}%) on the latest session.")
    if "^GSPC" in tel or "^IXIC" in tel:
        r = tel.get("^IXIC", tel.get("^GSPC"))
        market.append(f"US benchmark {r['label']} moved {r['delta_pct']:+.2f}% overnight to {r['value']:,.0f}.")
    market = market or ["Market telemetry unavailable this cycle."]

    arb = state["arbiter"] or (
        "Automated spillover analysis was unavailable this cycle; telemetry and "
        "headline ingestion completed normally and the next scheduled run will "
        "restore the full arbiter brief.")
    return {
        "market": market,
        "economic": pick("regional_macro", 2, "Regional macro"),
        "tech_ai": pick("tech_ai", 2, "Tech"),
        "political": pick("policy_sustainability", 2, "Policy"),
        "arbiter_brief": arb,
        "executive_brief": [
            market[0],
            pick("regional_macro", 1, "Regional macro")[0],
            pick("tech_ai", 1, "Tech")[0],
        ],
    }


# ---------------------------------------------------------------- graph wiring
def run_graph() -> dict:
    """LangGraph stateful execution with sequential fallback."""
    nodes = [("quant", node_quant), ("hunter", node_hunter),
             ("arbiter", node_arbiter), ("chief", node_chief)]
    try:
        from typing import TypedDict

        from langgraph.graph import END, START, StateGraph

        class CockpitState(TypedDict, total=False):
            telemetry: list
            anomaly: bool
            anomaly_desc: str
            headlines: dict
            signals: str
            arbiter: str
            compiled: dict

        g = StateGraph(CockpitState)
        for name, fn in nodes:
            g.add_node(name, fn)
        g.add_edge(START, "quant")
        g.add_edge("quant", "hunter")
        g.add_edge("hunter", "arbiter")
        g.add_edge("arbiter", "chief")
        g.add_edge("chief", END)
        print("[graph] executing via LangGraph state machine")
        return g.compile().invoke({})
    except ImportError:
        print("[graph] langgraph not installed — sequential execution")
        state: dict = {}
        for _, fn in nodes:
            state.update(fn(state))
        return state


# ---------------------------------------------------------------- contract
REQUIRED_SHAPE = {
    "timestamp": str,
    "opening": dict,
    "intelligence_quadrants": dict,
    "news": list,
    "sector_news": dict,
    "ticker_news": dict,
    "videos": list,
    "daily_brief": dict,
    "intelligence_health": dict,
    "note_of_the_day": str,
}

NEWS_CATEGORIES = {"ECONOMY", "TECH", "MARKETS_FINANCE", "CRYPTO"}
VIDEO_CATEGORIES = {"market_id", "market_us", "crypto"}


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"contract violation: {message}")


def _validate_brief(brief: dict) -> None:
    _expect(isinstance(brief.get("sentiment"), dict), "daily_brief.sentiment missing")
    _expect(isinstance(brief.get("synthesis"), str), "daily_brief.synthesis missing")
    for key in ("must_watch", "must_read", "key_themes"):
        _expect(isinstance(brief.get(key), list), f"daily_brief.{key} missing")
    for key in ("news_digest", "video_digest"):
        digest = brief.get(key)
        _expect(isinstance(digest, dict), f"daily_brief.{key} missing")
        for region in ("indonesia", "us"):
            _expect(isinstance(digest.get(region), str) and digest.get(region).strip(),
                    f"daily_brief.{key}.{region} missing")
    if "quality_audit" in brief:
        _expect(isinstance(brief.get("quality_audit"), dict), "daily_brief.quality_audit invalid")


def _validate_intelligence(payload: dict) -> None:
    for i, item in enumerate(payload["news"][:250]):
        _expect(isinstance(item.get("title"), str) and item.get("title").strip(),
                f"news[{i}].title missing")
        _expect(isinstance(item.get("url"), str) and item.get("url").startswith("http"),
                f"news[{i}].url missing")
        _expect(item.get("category") in NEWS_CATEGORIES,
                f"news[{i}].category invalid: {item.get('category')}")
    for i, item in enumerate(payload["videos"][:250]):
        _expect(isinstance(item.get("video_id"), str) and item.get("video_id").strip(),
                f"videos[{i}].video_id missing")
        _expect(item.get("category") in VIDEO_CATEGORIES,
                f"videos[{i}].category invalid: {item.get('category')}")
    health = payload["intelligence_health"]
    _expect(isinstance(health.get("news"), dict), "intelligence_health.news missing")
    _expect(isinstance(health.get("videos"), dict), "intelligence_health.videos missing")
    _expect(isinstance(health["news"].get("wire_count"), int), "intelligence_health.news.wire_count missing")
    _expect(isinstance(health["videos"].get("source_total"), int), "intelligence_health.videos.source_total missing")
    if "daily_brief" in health:
        _expect(isinstance(health.get("daily_brief"), dict), "intelligence_health.daily_brief invalid")
        _expect(isinstance(health["daily_brief"].get("noisy_reason_count"), int),
                "intelligence_health.daily_brief.noisy_reason_count missing")
    _validate_brief(payload["daily_brief"])


def validate(payload: dict) -> None:
    for key, typ in REQUIRED_SHAPE.items():
        if not isinstance(payload.get(key), typ):
            raise ValueError(f"contract violation: '{key}' missing or wrong type")
    op = payload["opening"]
    for key in ("greeting", "focus_state", "weather", "verse_of_the_day", "ambient_soundtrack"):
        if key not in op:
            raise ValueError(f"contract violation: opening.{key} missing")
    for key in ("bsd", "jakarta", "insight"):
        if not isinstance(op["weather"].get(key), str):
            raise ValueError(f"contract violation: opening.weather.{key}")
    for key in ("track_name", "embed_url"):
        if not isinstance(op["ambient_soundtrack"].get(key), str):
            raise ValueError(f"contract violation: ambient_soundtrack.{key}")
    iq = payload["intelligence_quadrants"]
    for key in ("market", "economic", "tech_ai", "political"):
        arr = iq.get(key)
        if not isinstance(arr, list) or not arr or not all(isinstance(s, str) for s in arr):
            raise ValueError(f"contract violation: intelligence_quadrants.{key}")
    _validate_intelligence(payload)


def compile_payload(state: dict) -> dict:
    wx = env_context.weather()
    rainy = wx.pop("_rainy", False)
    previous_note, previous_pods = None, []
    previous_videos, previous_brief, previous_sectors = [], None, []
    try:
        with open(settings.DATA_JSON_PATH, encoding="utf-8") as f:
            _prev = json.load(f)
            previous_note = _prev.get("note_of_the_day")
            previous_pods = _prev.get("podcasts", [])
            previous_videos = _prev.get("videos", [])
            previous_brief = _prev.get("daily_brief")
            previous_sectors = _prev.get("sectors", [])
    except Exception:  # noqa: BLE001 — first run has no file
        pass

    c = state["compiled"]
    has_llm = bool(settings.DEEPSEEK_API_KEY or settings.OPENROUTER_API_KEY)
    summarize = (lambda s, u: call_deepseek(s, u)) if has_llm else None

    sec = sectors.collect(previous_sectors, telemetry=state["telemetry"])
    _deepseek_sector_intel(sec, has_llm, previous_sectors)   # DeepSeek ai + structural themes
    news = news_router.enrich(state.get("headlines", {}), sec, state["telemetry"])
    vids = videos.collect(previous=previous_videos)
    brief = daily_brief.compile_brief(
        state["telemetry"], sec, news["wire"], vids, c["arbiter_brief"],
        summarize=summarize, previous=previous_brief)
    ma = macro_alerts.compile_macro_alerts(
        state["telemetry"], sec, news["wire"], vids,
        state.get("signals", ""), summarize=summarize)

    payload = {
        "timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "opening": {
            "greeting": env_context.greeting(),
            "focus_state": env_context.focus_state(),
            "weather": wx,
            "verse_of_the_day": env_context.verse_of_the_day(),
            "ambient_soundtrack": env_context.ambient_soundtrack(rainy, state["anomaly"]),
            "now_playing": spotify.now_playing(),
        },
        "telemetry": state["telemetry"],
        "anomaly": {"active": state["anomaly"], "desc": state["anomaly_desc"]},
        "intelligence_quadrants": {
            "market": c["market"], "economic": c["economic"],
            "tech_ai": c["tech_ai"], "political": c["political"],
        },
        "arbiter_brief": c["arbiter_brief"],
        "executive_brief": c["executive_brief"],
        "sectors": sec,
        "news": news["wire"],
        "sector_news": news["sector_news"],
        "ticker_news": news["ticker_news"],
        "videos": vids,
        "intelligence_health": {
            "news": news.get("audit", {}),
            "videos": videos.audit(vids),
            "daily_brief": brief.get("quality_audit", {}),
        },
        "daily_brief": brief,
        "macro_analysis": ma["macro_analysis"],
        "alerts": ma["alerts"],
        "trending": trending.collect(sec),
        "podcasts": podcasts.collect(summarize=summarize, previous=previous_pods),
        "coverage_universe": _coverage_universe_summary(sec),
        "config": {"finnhub_key": settings.FINNHUB_API_KEY},
        "note_of_the_day": env_context.note_of_the_day(previous_note),
        "generated_by": ("LangGraph pipeline · DeepSeek · yfinance / Google News / "
                         "Finnhub / Spotify / StockTwits · GitHub Actions cron"),
    }
    validate(payload)
    return payload


def _deepseek_sector_intel(sectors_list: list, has_llm: bool,
                           previous_sectors: list | None = None) -> None:
    """DeepSeek sector synthesis: a tight actionable paragraph (`ai`) AND 3 structural
    `themes`, in ONE JSON call per sector. WATCH/ALERT sectors regenerate every run;
    NORMAL sectors reuse the cached DeepSeek output (generated once, marked themes_ai)
    to bound cost. Falls back to the deterministic ai + settings.SECTOR_THEMES when no
    LLM is configured or a call/parse fails."""
    if not has_llm:
        return
    prev = {s.get("key"): s for s in (previous_sectors or [])}
    for s in sectors_list:
        cached = prev.get(s["key"])
        active = s["signal"] in ("WATCH", "ALERT")
        if not active and cached and cached.get("themes_ai") and cached.get("themes"):
            s["themes"] = cached["themes"]            # reuse cached DeepSeek themes (NORMAL)
            s["themes_ai"] = True
            if cached.get("ai"):
                s["ai"] = cached["ai"]
            continue
        cons = ", ".join(f"{c['ticker']} {c['delta_pct']:+.2f}%"
                         for c in s["constituents"][:8])
        split = (f"{s['idChange']:+.2f}% ID / {s['usChange']:+.2f}% US"
                 if s.get("idChange") is not None and s.get("usChange") is not None
                 else "global / no ID-US split")
        raw = call_deepseek(
            "You are an institutional analyst briefing an Indonesia-focused investor. "
            "Output RAW JSON only (no code fences): {\"ai\":\"one tight <=70-word "
            "actionable paragraph, no hedging\",\"themes\":[\"3 structural-theme bullets, "
            "each one specific full sentence on a durable driver of this sector\"]}. "
            "Plain text inside the values.",
            f"Sector: {s['name']} ({s['change']:+.2f}% agg, {split}, signal {s['signal']}). "
            f"Movers: {cons}.")
        obj = None
        if raw:
            txt = raw.strip()
            if txt.startswith("```"):
                txt = txt.strip("`")
                txt = txt[txt.find("{"):]
            try:
                obj = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
            except Exception:  # noqa: BLE001
                obj = None
        if obj:
            if isinstance(obj.get("ai"), str) and obj["ai"].strip():
                s["ai"] = obj["ai"].strip()
            th = obj.get("themes")
            if isinstance(th, list) and [t for t in th if str(t).strip()]:
                s["themes"] = [str(t).strip()[:200] for t in th[:4] if str(t).strip()]
                s["themes_ai"] = True


def write_atomic(payload: dict) -> None:
    target = os.path.abspath(settings.DATA_JSON_PATH)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, target)
    print(f"[worker] data contract written -> {target}")


def main() -> int:
    try:
        state = run_graph()
        payload = compile_payload(state)
        write_atomic(payload)
        return 0
    except Exception as e:  # noqa: BLE001 — failover: keep last valid data.json
        print(f"[worker] FATAL — existing data.json left undisturbed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
