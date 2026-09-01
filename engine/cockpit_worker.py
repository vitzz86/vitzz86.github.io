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
from tools import (daily_brief, enterprise_osint, env_context, ipos,  # noqa: E402
                   macro_alerts, macro_indicators, market_telemetry, news_router, podcasts,
                   research, sectors, trending, universe, videos)


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


VALUATION_SUMMARY_KEYS = {
    "status", "buy_below", "signal", "upside_pct", "current_price", "currency",
}

RISK_SUMMARY_KEYS = {
    "sharpe", "sortino", "max_drawdown_pct", "risk_adjusted_signal",
}


def _score_key(row: dict) -> str:
    country = str(row.get("country") or "")
    ticker = str(row.get("ticker") or row.get("source_symbol") or "")
    source_symbol = str(row.get("source_symbol") or "")
    sector_key = str(row.get("sector_key") or row.get("_payload_sector_key") or "")
    return f"{country}|{ticker}|{source_symbol}|{sector_key}"


def _score_summary(score: dict) -> dict:
    """Small score object for data.json; full detail lives in scores.json."""
    if not isinstance(score, dict):
        return {}
    out = {
        key: score.get(key)
        for key in (
            "mode", "schema_version", "score", "label", "coverage", "axes",
            "input_coverage", "axis_coverage", "confidence", "data_confidence_pct",
            "data_confidence_components",
            "currency", "source", "as_of", "note", "screen_grade",
            "quote_source", "screen_source", "data_warnings", "score_methodology",
            "limitations", "screening_score_legacy",
        )
        if key in score and score.get(key) is not None
    }
    out["metric_count"] = len(score.get("metrics") or [])
    valuation = score.get("valuation")
    if isinstance(valuation, dict):
        out["valuation"] = {
            key: valuation.get(key)
            for key in VALUATION_SUMMARY_KEYS
            if valuation.get(key) is not None
        }
    risk = score.get("risk_stats")
    if isinstance(risk, dict):
        out["risk_stats"] = {
            key: risk.get(key)
            for key in RISK_SUMMARY_KEYS
            if risk.get(key) is not None
        }
    ctx = score.get("risk_context")
    if isinstance(ctx, dict):
        out["risk_context"] = {
            key: ctx.get(key)
            for key in (
                "risk_free_rate", "risk_free_label", "risk_free_source",
                "hurdle_rate", "hurdle_label", "hurdle_source",
            )
            if ctx.get(key) is not None
        }
    return out


def _load_previous_scores() -> dict:
    try:
        with open(settings.SCORES_JSON_PATH, encoding="utf-8") as f:
            obj = json.load(f)
        return obj.get("scores", {}) if isinstance(obj, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _hydrate_previous_sector_scores(previous_sectors: list, score_map: dict) -> list:
    if not previous_sectors or not score_map:
        return previous_sectors
    for sec in previous_sectors:
        for row in sec.get("constituents", []) or []:
            ref = row.get("score_ref") or _score_key(row)
            if ref in score_map and row.get("fundamental_score"):
                row["fundamental_score"] = score_map[ref]
    return previous_sectors


def _load_previous_charts() -> dict:
    try:
        with open(settings.CHARTS_JSON_PATH, encoding="utf-8") as f:
            obj = json.load(f)
        return obj.get("charts", {}) if isinstance(obj, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _hydrate_previous_sector_charts(previous_sectors: list, chart_map: dict) -> list:
    if not previous_sectors or not chart_map:
        return previous_sectors
    for sec in previous_sectors:
        for row in sec.get("constituents", []) or []:
            ref = row.get("chart_ref") or _score_key(row)
            chart = chart_map.get(ref)
            if isinstance(chart, dict):
                for key in ("spark", "spark_ts", "intraday"):
                    if chart.get(key):
                        row[key] = chart[key]
    return previous_sectors


def _extract_score_payload(payload: dict) -> dict:
    scores: dict[str, dict] = {}
    for sec in payload.get("sectors", []) or []:
        for row in sec.get("constituents", []) or []:
            full = row.get("fundamental_score")
            if not isinstance(full, dict) or not full:
                continue
            ref = _score_key(row)
            scores[ref] = full
            row["score_ref"] = ref
            row["fundamental_score"] = _score_summary(full)
    return {
        "timestamp": payload.get("timestamp"),
        "schema": 1,
        "scores": scores,
    }


def _extract_chart_payload(payload: dict) -> dict:
    charts: dict[str, dict] = {}
    for sec in payload.get("sectors", []) or []:
        for row in sec.get("constituents", []) or []:
            detail = {
                key: row.get(key)
                for key in ("spark", "spark_ts", "intraday")
                if row.get(key)
            }
            if not detail:
                continue
            ref = _score_key(row)
            charts[ref] = detail
            row["chart_ref"] = ref
            row.pop("spark", None)
            row.pop("spark_ts", None)
            row.pop("intraday", None)
    return {
        "timestamp": payload.get("timestamp"),
        "schema": 1,
        "charts": charts,
    }


MCP_ASSET_KEYS = {
    "ticker", "name", "source_symbol", "country", "country_name", "country_flag",
    "exchange", "region", "industry", "sector_key", "sector_name", "tier",
    "index_groups", "value", "delta_pct", "market_cap_value", "mktcap", "volume",
    "volume_24h", "avg_volume_10d", "avg_volume_30d", "relative_volume_10d",
    "turnover", "state", "quote_asof", "quote_mode", "chart_asof", "chart_quality",
    "data_tier", "source_name", "source_provider", "source_url", "url",
    "score_ref", "chart_ref", "perf_1w", "perf_1m", "perf_3m", "perf_6m",
    "perf_1y", "perf_ytd", "analyst_target_low", "analyst_target_median",
    "analyst_target_high", "recommend_all", "rsi", "volatility_1d",
    "volatility_1w", "volatility_1m", "listing_ts",
    "return_quality", "quote_return_source", "market_data_warning",
}


def _extract_mcp_assets(payload: dict) -> dict:
    """Compact asset universe loaded only by market and company MCP tools."""
    sectors_out = []
    asset_count = 0
    for sector in payload.get("sectors", []) or []:
        constituents = []
        for row in sector.get("constituents", []) or []:
            compact = {key: row.get(key) for key in MCP_ASSET_KEYS
                       if row.get(key) is not None}
            compact.setdefault("sector_key", sector.get("key"))
            compact.setdefault("sector_name", sector.get("name"))
            constituents.append(compact)
        asset_count += len(constituents)
        sectors_out.append({
            key: sector.get(key)
            for key in ("key", "name", "icon", "change", "idChange", "usChange",
                        "signal", "themes", "themes_ai", "ai")
            if sector.get(key) is not None
        } | {"constituents": constituents})

    return {
        "timestamp": payload.get("timestamp"),
        "schema": 1,
        "contract": "project_cockpit_mcp_assets",
        "asset_count": asset_count,
        "sectors": sectors_out,
    }


def _extract_mcp_payload(payload: dict) -> dict:
    """Compact intelligence contract for the public MCP Worker.

    The dashboard keeps rich sector rows in data.json; the asset universe is a
    separate lazy contract, and score/chart details remain independently lazy.
    """
    keep = (
        "timestamp", "telemetry", "trending", "news", "ticker_news", "videos",
        "podcasts", "daily_brief", "macro_analysis", "alerts", "arbiter_brief",
        "ipo", "research", "macro_indicators", "intelligence_health",
        "coverage_universe", "config",
    )
    out = {key: payload.get(key) for key in keep if key in payload}
    out.update({
        "schema": 1,
        "contract": "project_cockpit_mcp",
        "asset_count": sum(len(sector.get("constituents", []) or [])
                           for sector in payload.get("sectors", []) or []),
    })
    return out


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
    "ipo": dict,
    "research": dict,
    "macro_indicators": dict,
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
    ipo = payload.get("ipo") or {}
    for key in ("recent_id", "recent_us", "upcoming_id", "upcoming_us",
                "pipeline_id", "pipeline_us", "sp500_changes"):
        _expect(isinstance(ipo.get(key), list), f"ipo.{key} missing")
    _expect(isinstance(ipo.get("health"), dict), "ipo.health missing")
    synthesis = ipo.get("synthesis")
    _expect(isinstance(synthesis, dict), "ipo.synthesis missing")
    for view in ("upcoming", "pipeline", "recent", "changes"):
        block = synthesis.get(view)
        _expect(isinstance(block, dict), f"ipo.synthesis.{view} missing")
        for region in ("indonesia", "us"):
            _expect(isinstance(block.get(region), str) and block.get(region).strip(),
                    f"ipo.synthesis.{view}.{region} missing")
    research_payload = payload.get("research") or {}
    _expect(isinstance(research_payload.get("reports"), list), "research.reports missing")
    _expect(isinstance(research_payload.get("health"), dict), "research.health missing")
    macro_payload = payload.get("macro_indicators") or {}
    for key in ("core", "detail", "ratings", "country_risk"):
        _expect(isinstance(macro_payload.get(key), list), f"macro_indicators.{key} missing")
    _expect(len(macro_payload.get("core") or []) >= 12,
            "macro_indicators.core must contain at least 12 headline indicators")
    for group in ("core", "detail", "ratings", "country_risk"):
        for i, item in enumerate(macro_payload.get(group) or []):
            _expect(isinstance(item.get("label"), str) and item.get("label").strip(),
                    f"macro_indicators.{group}[{i}].label missing")
            _expect(isinstance(item.get("source_url"), str) and item.get("source_url").startswith("http"),
                    f"macro_indicators.{group}[{i}].source_url missing")


def validate(payload: dict) -> None:
    for key, typ in REQUIRED_SHAPE.items():
        if not isinstance(payload.get(key), typ):
            raise ValueError(f"contract violation: '{key}' missing or wrong type")
    op = payload["opening"]
    for key in ("greeting", "focus_state", "weather", "verse_of_the_day"):
        if key not in op:
            raise ValueError(f"contract violation: opening.{key} missing")
    for key in ("bsd", "jakarta", "insight"):
        if not isinstance(op["weather"].get(key), str):
            raise ValueError(f"contract violation: opening.weather.{key}")
    iq = payload["intelligence_quadrants"]
    for key in ("market", "economic", "tech_ai", "political"):
        arr = iq.get(key)
        if not isinstance(arr, list) or not arr or not all(isinstance(s, str) for s in arr):
            raise ValueError(f"contract violation: intelligence_quadrants.{key}")
    chart_health = (((payload.get("coverage_universe") or {}).get("source_health") or {}).get("charts") or {})
    _expect(chart_health.get("status") == "complete_routes",
            f"chart routes incomplete: {chart_health.get('missing_routes') or 'audit missing'}")
    _expect(chart_health.get("route_ready") == chart_health.get("total"),
            "chart route count does not cover the active universe")
    _expect(not chart_health.get("quality_mismatches"),
            f"chart quality labels mismatch their series: {chart_health.get('quality_mismatches')}")
    sector_rows = [row for sector in payload.get("sectors", [])
                   for row in sector.get("constituents", [])]
    index_counts = {
        group: sum(group in (row.get("index_groups") or []) for row in sector_rows)
        for group in ("sp500", "nasdaq100")
    }
    if getattr(settings, "SP500_PRICE_ACTIVE", False):
        _expect(index_counts["sp500"] >= 490,
                f"S&P 500 membership incomplete: {index_counts['sp500']} rows")
    if getattr(settings, "NASDAQ100_PRICE_ACTIVE", False):
        _expect(index_counts["nasdaq100"] >= 90,
                f"Nasdaq 100 membership incomplete: {index_counts['nasdaq100']} rows")
    _validate_intelligence(payload)


def compile_payload(state: dict) -> tuple[dict, dict, dict, dict, dict]:
    wx = env_context.weather()
    wx.pop("_rainy", False)
    previous_note, previous_pods = None, []
    previous_videos, previous_brief, previous_sectors, previous_ipo, previous_research = [], None, [], {}, {}
    previous_score_map = _load_previous_scores()
    previous_chart_map = _load_previous_charts()
    try:
        with open(settings.DATA_JSON_PATH, encoding="utf-8") as f:
            _prev = json.load(f)
            previous_note = _prev.get("note_of_the_day")
            previous_pods = _prev.get("podcasts", [])
            previous_videos = _prev.get("videos", [])
            previous_brief = _prev.get("daily_brief")
            previous_ipo = _prev.get("ipo") or {}
            previous_research = _prev.get("research") or {}
            previous_sectors = _prev.get("sectors", [])
            previous_sectors = _hydrate_previous_sector_scores(previous_sectors, previous_score_map)
            previous_sectors = _hydrate_previous_sector_charts(previous_sectors, previous_chart_map)
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
    ipo = ipos.collect(sec, previous=previous_ipo, news_wire=news["wire"], summarize=summarize)
    research_library = research.collect(sec, previous=previous_research)
    macro_dashboard = macro_indicators.collect(state["telemetry"])

    payload = {
        "timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "opening": {
            "greeting": env_context.greeting(),
            "focus_state": env_context.focus_state(),
            "weather": wx,
            "verse_of_the_day": env_context.verse_of_the_day(),
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
        "ipo": ipo,
        "research": research_library,
        "macro_indicators": macro_dashboard,
        "trending": trending.collect(sec),
        "podcasts": podcasts.collect(summarize=summarize, previous=previous_pods),
        "coverage_universe": _coverage_universe_summary(sec),
        "config": {
            "realtime_proxy_url": settings.REALTIME_PROXY_URL,
            "realtime_stream_url": settings.REALTIME_STREAM_URL,
            "idx_fast_quote_url": settings.IDX_FAST_QUOTE_URL,
            "snapshot_refresh_minutes": 30,
        },
        "note_of_the_day": env_context.note_of_the_day(previous_note),
        "generated_by": ("LangGraph pipeline · DeepSeek · TradingView IDX / yfinance / "
                         "Google News / broker research / StockTwits · GitHub Actions cron"),
    }
    validate(payload)
    scores_payload = _extract_score_payload(payload)
    charts_payload = _extract_chart_payload(payload)
    mcp_payload = _extract_mcp_payload(payload)
    mcp_assets_payload = _extract_mcp_assets(payload)
    return payload, scores_payload, charts_payload, mcp_payload, mcp_assets_payload


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
        moved = False
        if cached:
            for field in ("change", "idChange", "usChange"):
                current, old = s.get(field), cached.get(field)
                if current is not None and old is not None and abs(float(current) - float(old)) >= 0.20:
                    moved = True
                    break
        if not active and not moved and cached and cached.get("themes_ai") and cached.get("themes"):
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


def _write_json_atomic(path: str, payload: dict) -> None:
    target = os.path.abspath(path)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, target)


def write_atomic(payload: dict, scores_payload: dict | None = None,
                 charts_payload: dict | None = None,
                 mcp_payload: dict | None = None,
                 mcp_assets_payload: dict | None = None) -> None:
    if scores_payload is not None:
        _write_json_atomic(settings.SCORES_JSON_PATH, scores_payload)
        print(f"[worker] score detail contract written -> {os.path.abspath(settings.SCORES_JSON_PATH)}")
    if charts_payload is not None:
        _write_json_atomic(settings.CHARTS_JSON_PATH, charts_payload)
        print(f"[worker] chart detail contract written -> {os.path.abspath(settings.CHARTS_JSON_PATH)}")
    if mcp_payload is not None:
        _write_json_atomic(settings.MCP_JSON_PATH, mcp_payload)
        print(f"[worker] MCP contract written -> {os.path.abspath(settings.MCP_JSON_PATH)}")
    if mcp_assets_payload is not None:
        _write_json_atomic(settings.MCP_ASSETS_JSON_PATH, mcp_assets_payload)
        print(f"[worker] MCP asset contract written -> {os.path.abspath(settings.MCP_ASSETS_JSON_PATH)}")
    shell_payload = {
        key: value for key, value in payload.items()
        if key not in {"sectors", "ticker_news", "research"}
    }
    shell_payload["sectors"] = []
    shell_payload["ticker_news"] = {}
    shell_payload["research"] = {}
    shell_payload["asset_count"] = sum(len(sector.get("constituents", [])) for sector in payload.get("sectors", []))
    _write_json_atomic(settings.COCKPIT_SHELL_JSON_PATH, shell_payload)
    print(f"[worker] cockpit shell written -> {os.path.abspath(settings.COCKPIT_SHELL_JSON_PATH)}")
    _write_json_atomic(settings.COCKPIT_DETAIL_JSON_PATH, {
        "timestamp": payload.get("timestamp"),
        "ticker_news": payload.get("ticker_news") or {},
        "research": payload.get("research") or {},
    })
    print(f"[worker] cockpit detail written -> {os.path.abspath(settings.COCKPIT_DETAIL_JSON_PATH)}")
    _write_json_atomic(settings.DATA_JSON_PATH, payload)
    print(f"[worker] data contract written -> {os.path.abspath(settings.DATA_JSON_PATH)}")


def main() -> int:
    try:
        state = run_graph()
        (payload, scores_payload, charts_payload, mcp_payload,
         mcp_assets_payload) = compile_payload(state)
        write_atomic(payload, scores_payload, charts_payload, mcp_payload,
                     mcp_assets_payload)
        return 0
    except Exception as e:  # noqa: BLE001 — failover: keep last valid data.json
        print(f"[worker] FATAL — existing data.json left undisturbed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
