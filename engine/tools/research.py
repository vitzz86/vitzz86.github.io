"""Curated and discovered investment-research evidence for Cockpit and MCP."""
from __future__ import annotations

import datetime as dt
import concurrent.futures as cf
import hashlib
import json
import re
from pathlib import Path

from config import settings
from tools import news_router


REFRESH_SECONDS = 6 * 3600
RETENTION_SECONDS = 366 * 86400
LIBRARY_PATH = Path(__file__).resolve().parents[1] / "config" / "research_library.json"
REGIONS = ("Global", "SEA", "APAC", "Indonesia")
REPORT_TYPES = (
    "Economics & Macro",
    "Equity Research",
    "Market Strategy",
    "Fixed Income & Credit",
    "Private Markets & Venture",
    "Industry & Thematic",
)


def _now() -> int:
    return int(dt.datetime.now(dt.timezone.utc).timestamp())


def _clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _key(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).lower()).strip()


def _region(value: str) -> str:
    geography = _key(value)
    if "indonesia" in geography:
        return "Indonesia"
    if any(term in geography for term in (
        "southeast asia", "asean", "vietnam", "thailand", "singapore", "malaysia",
        "philippines", "brunei", "cambodia", "laos", "myanmar",
    )) and "asean 3" not in geography:
        return "SEA"
    if any(term in geography for term in (
        "apac", "asia pacific", "asia", "china", "japan", "korea", "taiwan",
        "hong kong", "india", "australia", "new zealand", "asean 3",
    )):
        return "APAC"
    return "Global"


def _report_type(item: dict) -> str:
    value = _key(" ".join(_clean(item.get(field)) for field in (
        "title", "category", "subcategory", "coverage", "why_useful",
    )))
    if any(term in value for term in (
        "fixed income", "bond", "bonds", "credit", "sukuk", "yield curve", "direct lending",
    )):
        return "Fixed Income & Credit"
    if any(term in value for term in (
        "private market", "private equity", "venture", "startup", "fundraising", "pre seed",
        "growth equity", "deal activity",
    )):
        return "Private Markets & Venture"
    if any(term in value for term in (
        "economic", "economy", "macroeconomic", "macro ", "inflation", "gdp", "monetary policy",
        "fiscal policy", "financial stability", "country outlook", "rupiah",
    )):
        return "Economics & Macro"
    if item.get("ticker_tags") or any(term in value for term in (
        "company update", "company report", "initiation", "earnings", "results review",
        "target price", "stock call", "equity research",
    )):
        return "Equity Research"
    if any(term in value for term in (
        "sector", "industry", "thematic", "climate", "technology", "artificial intelligence",
        "digital health", "insurtech", "infrastructure", "real estate",
    )):
        return "Industry & Thematic"
    return "Market Strategy"


def _normalize_item(item: dict) -> dict:
    normalized = dict(item)
    original_geography = _clean(normalized.get("geography_detail") or normalized.get("geography"))
    original_category = _clean(normalized.get("category_detail") or normalized.get("category"))
    normalized["geography_detail"] = original_geography
    normalized["geography"] = _region(original_geography)
    normalized["category_detail"] = original_category
    normalized["category"] = _report_type(normalized)
    normalized["report_type"] = normalized["category"]
    return normalized


def _curated() -> list[dict]:
    try:
        payload = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[research] curated library unavailable: {exc}")
        return []
    return [_normalize_item(item) for item in payload.get("reports") or []]


def _asset_terms(sectors: list) -> tuple[set[str], list[tuple[str, str]]]:
    tickers, names = set(), []
    for sector in sectors or []:
        for asset in sector.get("constituents") or []:
            if asset.get("country") != "ID":
                continue
            ticker = _clean(asset.get("ticker")).upper()
            name = _clean(asset.get("name"))
            if ticker:
                tickers.add(ticker)
            if ticker and name and len(name) >= 5:
                names.append((ticker, _key(name)))
    return tickers, names


def _ticker_tags(title: str, tickers: set[str], names: list[tuple[str, str]]) -> list[str]:
    raw, normalized = _clean(title), _key(title)
    tags = {token for token in re.findall(r"\b[A-Z]{4}\b", raw) if token in tickers}
    for ticker, name in names:
        if name and name in normalized:
            tags.add(ticker)
    return sorted(tags)[:12]


def _classify(title: str) -> tuple[str, str]:
    value = _key(title)
    if any(term in value for term in ("fixed income", "bond", "credit", "sukuk", "rates")):
        return "Fixed Income & Credit", "Fixed Income"
    if any(term in value for term in ("startup", "venture", "private equity", "fundraising", "deals")):
        return "Private Markets & Venture", "Startup / VC"
    if any(term in value for term in ("economic", "macro", "inflation", "gdp", "policy", "rupiah")):
        return "Economics & Macro", "Macro / Strategy"
    if any(term in value for term in ("sector", "industry", "strategy", "outlook")):
        return "Industry & Thematic", "Sector / Strategy"
    return "Equity Research", "Company / Equity"


def _discover_source(source: dict, tickers: set[str], names: list[tuple[str, str]]) -> tuple[str, list[dict]]:
    try:
        rows = news_router.google_news(
            source["query"], geo=source.get("geo", "ID"), n=source.get("limit", 5),
            site=source["domain"], query_type="research", days=source.get("days", 45),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[research] {source['name']} discovery failed: {exc}")
        return source["name"], []
    reports = []
    for row in rows:
        title = _clean(row.get("title"))
        tags = _ticker_tags(title, tickers, names)
        hay = _key(" ".join([title, row.get("summary") or ""]))
        if not title or (not tags and not any(term in hay for term in settings.RESEARCH_EVIDENCE_TERMS)):
            continue
        category, subcategory = _classify(title)
        url = row.get("url")
        if not url:
            continue
        report_id = "live-" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
        reports.append(_normalize_item({
            "id": report_id, "priority": "Live", "category": category,
            "subcategory": subcategory, "geography": source.get("geography", "Indonesia"),
            "title": title, "publisher": source["name"],
            "published": dt.datetime.fromtimestamp(int(row.get("ts") or _now()), dt.timezone.utc).strftime("%Y-%m-%d"),
            "published_ts": int(row.get("ts") or 0), "coverage": "Latest research discovery",
            "format": "Research landing page", "access": "Open / verify at source",
            "direct_url": "", "landing_url": url, "source_url": url,
            "relevance": "Current", "why_useful": _clean(row.get("summary")) or "Current broker or institutional research evidence; open the source before relying on its conclusions.",
            "verification": "Discovered from official publisher domain", "verified_on": dt.date.today().isoformat(),
            "source_type": "official_discovery", "ticker_tags": tags,
            "sector_tags": [], "summary_basis": "publisher excerpt" if row.get("summary") else "title and metadata only",
        }))
    return source["name"], reports


def _discover(sectors: list) -> tuple[list[dict], dict]:
    tickers, names = _asset_terms(sectors)
    reports, source_counts = [], {}
    workers = min(6, max(1, len(settings.RESEARCH_DISCOVERY_SOURCES)))
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_discover_source, source, tickers, names)
                   for source in settings.RESEARCH_DISCOVERY_SOURCES]
        for future in cf.as_completed(futures):
            name, rows = future.result()
            reports.extend(rows)
            source_counts[name] = len(rows)
    return reports, source_counts


def _merge(curated: list[dict], discovered: list[dict], previous: list[dict]) -> list[dict]:
    cutoff = _now() - RETENTION_SECONDS
    pool = [_normalize_item(item) for item in (
        curated + discovered + [dict(item) for item in previous if item.get("source_type") == "official_discovery"]
    )]
    seen, out = set(), []
    for item in pool:
        if item.get("source_type") == "official_discovery" and int(item.get("published_ts") or 0) < cutoff:
            continue
        identity = item.get("source_url") or _key(item.get("title"))
        if not identity or identity in seen:
            continue
        seen.add(identity)
        item["source_url"] = item.get("source_url") or item.get("direct_url") or item.get("landing_url")
        item.setdefault("summary_basis", "curated index metadata")
        out.append(item)
    priority = {"Essential": 0, "High": 1, "Live": 2, "Supplementary": 3}
    return sorted(out, key=lambda item: (
        priority.get(_clean(item.get("priority")), 4),
        -int(item.get("published_ts") or 0), _clean(item.get("publisher")), _clean(item.get("title")),
    ))


def _synthesis(reports: list[dict]) -> dict:
    regional = [item for item in reports if item.get("geography") in {"Indonesia", "SEA", "APAC"}]
    open_count = sum("open" in _key(item.get("access")) or bool(item.get("direct_url")) for item in reports)
    publishers = len({_clean(item.get("publisher")) for item in reports if item.get("publisher")})
    return {
        "indonesia": f"{len(regional)} Indonesia, SEA, or APAC research records are indexed across economics, equities, strategy, credit, private markets, and thematic research.",
        "global": f"{len(reports)} verified research records from {publishers} publishers are searchable; {open_count} expose an open or direct-download route.",
    }


def collect(sectors: list, previous: dict | None = None) -> dict:
    previous = previous or {}
    previous_reports = list(previous.get("reports") or [])
    previous_asof = int(previous.get("discovery_as_of") or 0)
    if previous_asof and _now() - previous_asof < REFRESH_SECONDS:
        discovered = [item for item in previous_reports if item.get("source_type") == "official_discovery"]
        source_counts = dict((previous.get("health") or {}).get("source_counts") or {})
        discovery_state = "cached"
        discovery_asof = previous_asof
    else:
        discovered, source_counts = _discover(sectors)
        discovery_state = "live" if discovered else "no_new_results"
        discovery_asof = _now()
    reports = _merge(_curated(), discovered, previous_reports)
    payload = {
        "as_of": _now(), "discovery_as_of": discovery_asof,
        "reports": reports, "synthesis": _synthesis(reports),
        "health": {
            "status": "ready" if reports else "unavailable", "discovery": discovery_state,
            "report_count": len(reports), "curated_count": sum(item.get("source_type") == "curated_index" for item in reports),
            "live_count": sum(item.get("source_type") == "official_discovery" for item in reports),
            "ticker_tagged_count": sum(bool(item.get("ticker_tags")) for item in reports),
            "source_counts": source_counts,
            "regions": list(REGIONS), "report_types": list(REPORT_TYPES),
            "refresh_interval_seconds": REFRESH_SECONDS,
            "next_discovery_after": discovery_asof + REFRESH_SECONDS,
        },
        "provenance_note": "Research records are source-linked metadata. Cockpit does not reproduce full reports or treat broker opinions as facts.",
    }
    print(f"[research] {len(reports)} reports · {payload['health']['live_count']} live · {payload['health']['ticker_tagged_count']} ticker-tagged")
    return payload
