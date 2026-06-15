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
from tools import (enterprise_osint, env_context, market_telemetry,  # noqa: E402
                   news_router, podcasts, sectors, spotify, trending)


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
    try:
        r = requests.post(url, headers=headers, json={
            "model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.4,
            "max_tokens": settings.LLM_MAX_TOKENS,
        }, timeout=settings.LLM_TIMEOUT_S)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:  # noqa: BLE001
        print(f"[llm] DeepSeek call failed: {e}")
        return None


# ---------------------------------------------------------------- graph nodes
def node_quant(state: dict) -> dict:
    tel = market_telemetry.collect()
    print(f"[quant] {len(tel['rows'])} tickers, anomaly={tel['anomaly']}")
    return {"telemetry": tel["rows"], "anomaly": tel["anomaly"],
            "anomaly_desc": tel["anomaly_desc"]}


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
    tel_str = "\n".join(f"{r['label']}: {r['value']} ({r['delta_pct']:+.2f}%)"
                        for r in state["telemetry"])
    brief = call_deepseek(
        pt.ARBITER_PERSONA,
        pt.ARBITER_TASK.format(telemetry=tel_str or "unavailable",
                               signals=state["signals"] or "unavailable"))
    print(f"[arbiter] brief={'llm' if brief else 'fallback pending'}")
    return {"arbiter": brief or ""}


def node_chief(state: dict) -> dict:
    tel_str = "\n".join(f"{r['label']}: {r['value']} ({r['delta_pct']:+.2f}%)"
                        for r in state["telemetry"])
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
    "note_of_the_day": str,
}


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


def compile_payload(state: dict) -> dict:
    wx = env_context.weather()
    rainy = wx.pop("_rainy", False)
    previous_note = None
    try:
        with open(settings.DATA_JSON_PATH, encoding="utf-8") as f:
            previous_note = json.load(f).get("note_of_the_day")
    except Exception:  # noqa: BLE001 — first run has no file
        pass

    c = state["compiled"]
    has_llm = bool(settings.DEEPSEEK_API_KEY or settings.OPENROUTER_API_KEY)
    summarize = (lambda s, u: call_deepseek(s, u)) if has_llm else None

    sec = sectors.collect()
    _deepseek_sector_ai(sec, has_llm)                 # real AI text for WATCH/ALERT sectors
    news = news_router.enrich(state.get("headlines", {}), sec, state["telemetry"])

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
        "trending": trending.collect(sec),
        "podcasts": podcasts.collect(summarize=summarize),
        "config": {"finnhub_key": settings.FINNHUB_API_KEY},
        "note_of_the_day": env_context.note_of_the_day(previous_note),
        "generated_by": ("LangGraph pipeline · DeepSeek · yfinance / Google News / "
                         "Finnhub / Spotify / StockTwits · GitHub Actions cron"),
    }
    validate(payload)
    return payload


def _deepseek_sector_ai(sectors_list: list, has_llm: bool) -> None:
    """Upgrade the deterministic sector synthesis to real DeepSeek analysis for
    sectors flagged WATCH/ALERT (keeps cost bounded; NORMAL keeps the baked line)."""
    if not has_llm:
        return
    for s in sectors_list:
        if s["signal"] == "NORMAL":        # WATCH + ALERT get real AI; NORMAL stays deterministic
            continue
        cons = ", ".join(f"{c['ticker']} {c['delta_pct']:+.2f}%"
                         for c in s["constituents"][:8])
        out = call_deepseek(
            "You are an institutional analyst. Write ONE tight paragraph (<=70 words) of "
            "actionable cross-market intelligence for an Indonesia-focused investor. No hedging.",
            f"Sector: {s['name']} ({s['change']:+.2f}% agg, {s['idChange']:+.2f}% ID / "
            f"{s['usChange']:+.2f}% US, signal {s['signal']}). Movers: {cons}. "
            f"Themes: {'; '.join(s.get('themes', []))}.")
        if out:
            s["ai"] = out.strip()


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
