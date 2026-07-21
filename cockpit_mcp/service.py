"""Read-only query layer for Project Cockpit's static intelligence payloads."""

from __future__ import annotations

import html
import json
import math
import os
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


TIMEFRAME_DAYS = {"1W": 7, "1M": 31, "3M": 93, "6M": 190}
CONTRACT_FILES = {"data.json", "scores.json", "charts.json"}
MAX_CONTRACT_BYTES = 32 * 1024 * 1024
MARKET_ALIASES = {
    "id": "ID",
    "idx": "ID",
    "indonesia": "ID",
    "us": "US",
    "usa": "US",
    "sp500": "US",
    "nasdaq": "US",
    "crypto": "CR",
    "cr": "CR",
    "global": "ALL",
    "all": "ALL",
    "others": "OTHERS",
}


def _clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean_text(value).lower()).strip()


def _tokens(value: Any) -> List[str]:
    return [token for token in _norm(value).split() if len(token) > 1]


def _finite(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _iso(ts: Any) -> Optional[str]:
    number = _finite(ts)
    if number is None:
        return None
    return datetime.fromtimestamp(number, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _clamp_limit(limit: Any, default: int = 10, maximum: int = 50) -> int:
    try:
        return max(1, min(maximum, int(limit)))
    except (TypeError, ValueError):
        return default


def _market_code(value: str) -> str:
    raw = str(value or "all").strip().lower()
    return MARKET_ALIASES.get(raw, raw.upper())


def _title_key(value: Any) -> str:
    return " ".join(_tokens(value))


def _public_news(item: Dict[str, Any], must_read: bool = False) -> Dict[str, Any]:
    summary = _clean_text(item.get("summary"))
    return {
        "title": _clean_text(item.get("title")),
        "source": _clean_text(item.get("source")),
        "published_at": _iso(item.get("ts")),
        "market": item.get("geo"),
        "category": item.get("category"),
        "sectors": item.get("sectors") or [],
        "url": item.get("url"),
        "relevance_score": item.get("score"),
        "source_tier": item.get("source_tier") or "unranked",
        "must_read": must_read,
        "summary": summary or None,
        "summary_basis": "publisher excerpt" if summary else "headline and metadata only",
    }


def _public_video(item: Dict[str, Any], must_watch: bool = False) -> Dict[str, Any]:
    summary = _clean_text(item.get("summary") or item.get("thesis"))
    published = item.get("published") or _iso(item.get("ts"))
    return {
        "video_id": item.get("video_id"),
        "title": _clean_text(item.get("title")),
        "channel": _clean_text(item.get("channel") or item.get("show")),
        "published_at": published,
        "market": item.get("geo"),
        "category": item.get("category"),
        "duration_seconds": item.get("duration_s"),
        "url": item.get("url"),
        "embed_url": item.get("embed"),
        "thumbnail_url": item.get("thumb"),
        "must_watch": must_watch,
        "summary": summary or None,
        "summary_basis": "stored Cockpit synthesis" if summary else "title and metadata only",
        "collection": item.get("_collection", "intelligence_hub"),
    }


def _public_research(item: Dict[str, Any]) -> Dict[str, Any]:
    basis = item.get("summary_basis") or "source metadata only"
    has_content = bool(re.search(r"excerpt|abstract|full text|full report", str(basis), re.I))
    return {
        "id": item.get("id"),
        "title": _clean_text(item.get("title")),
        "publisher": _clean_text(item.get("publisher")),
        "published": item.get("published"),
        "published_ts": _finite(item.get("published_ts")),
        "priority": item.get("priority"),
        "category": item.get("category"),
        "report_type": item.get("report_type") or item.get("category"),
        "category_detail": item.get("category_detail"),
        "subcategory": item.get("subcategory"),
        "geography": item.get("geography"),
        "geography_detail": item.get("geography_detail"),
        "coverage": _clean_text(item.get("coverage")),
        "access": item.get("access"),
        "format": item.get("format"),
        "ticker_tags": item.get("ticker_tags") or [],
        "sector_tags": item.get("sector_tags") or [],
        "why_useful": _clean_text(item.get("why_useful")) or None,
        "direct_url": item.get("direct_url") or None,
        "landing_url": item.get("landing_url") or None,
        "source_url": item.get("source_url") or item.get("direct_url") or item.get("landing_url"),
        "source_type": item.get("source_type"),
        "verification": item.get("verification"),
        "verified_on": item.get("verified_on"),
        "summary_basis": basis,
        "evidence_scope": "content_excerpt_available" if has_content else "discovery_metadata_only",
        "claim_use": ("May support bounded claims attributed to the publisher." if has_content
                      else "Use to discover the report; open source_url before claiming the report's conclusions."),
    }


def _parse_research_date(value: Any, end: bool = False) -> Optional[float]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        if re.fullmatch(r"\d{4}", raw):
            year = int(raw)
            return datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp() - 1 if end \
                else datetime(year, 1, 1, tzinfo=timezone.utc).timestamp()
        if re.fullmatch(r"\d{4}-\d{2}", raw):
            year, month = map(int, raw.split("-"))
            if end:
                next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
                return datetime(next_year, next_month, 1, tzinfo=timezone.utc).timestamp() - 1
            return datetime(year, month, 1, tzinfo=timezone.utc).timestamp()
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        if end and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            return parsed.timestamp() + 86399
        return parsed.timestamp()
    except (ValueError, OverflowError):
        return None


def _research_date_bounds(date_from: str = "", date_to: str = "", year: Any = None,
                          period: str = "") -> Dict[str, Any]:
    start = _parse_research_date(date_from)
    end = _parse_research_date(date_to, True)
    match = re.search(r"(?:H([12])\s*(\d{4})|(\d{4})\s*H([12]))", str(period or "").upper())
    half_only = re.search(r"\bH([12])\b", str(period or "").upper())
    selected_year = int(year) if str(year or "").isdigit() else int(match.group(2) or match.group(3)) if match else 0
    half = int((match.group(1) or match.group(4)) if match else (half_only.group(1) if half_only else 0))
    if selected_year and start is None:
        start = datetime(selected_year, 7 if half == 2 else 1, 1, tzinfo=timezone.utc).timestamp()
    if selected_year and end is None:
        end_month = 7 if half == 1 else 1
        end_year = selected_year if half == 1 else selected_year + 1
        end = datetime(end_year, end_month, 1, tzinfo=timezone.utc).timestamp() - 1
    return {"from": start, "to": end, "date_from": _iso(start), "date_to": _iso(end),
            "period": str(period or "").upper() or None}


def _research_coverage(rows: Sequence[Dict[str, Any]], requested_publishers: Sequence[str]) -> Dict[str, Any]:
    def count_by(key: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in rows:
            value = _clean_text(item.get(key)) or "Unknown"
            counts[value] = counts.get(value, 0) + 1
        return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))

    present = sorted({_clean_text(item.get("publisher")) for item in rows if item.get("publisher")})
    requested = [_clean_text(value) for value in requested_publishers if _clean_text(value)]
    missing = [wanted for wanted in requested if not any(
        _norm(wanted) in _norm(value) or _norm(value) in _norm(wanted) for value in present)]
    metadata_only = sum(not re.search(r"excerpt|abstract|full text|full report",
                                     str(item.get("summary_basis") or ""), re.I) for item in rows)
    return {
        "requested_publishers": requested, "present_publishers": present,
        "missing_publishers": missing, "publisher_counts": count_by("publisher"),
        "category_counts": count_by("category"), "geography_counts": count_by("geography"),
        "access_counts": count_by("access"),
        "open_or_direct_count": sum(bool(re.search(r"open|download|public", str(item.get("access") or ""), re.I)
                                         or item.get("direct_url")) for item in rows),
        "metadata_only_count": metadata_only, "content_evidence_count": len(rows) - metadata_only,
        "source_open_required_count": metadata_only,
    }


def _chart_assessment(points: Sequence[Dict[str, Any]], quality: str, timeframe: str,
                      timestamp_basis: str) -> Dict[str, Any]:
    valid = [( _finite(point.get("timestamp") or point.get("ts")), _finite(point.get("value")) ) for point in points]
    valid = [(ts, value) for ts, value in valid if ts is not None and value is not None]
    # Local chart points expose ISO timestamps, so parse those separately.
    if not valid:
        valid = [(_parse_research_date(point.get("timestamp")), _finite(point.get("value"))) for point in points]
        valid = [(ts, value) for ts, value in valid if ts is not None and value is not None]
    peak: Optional[Tuple[float, float]] = None
    max_drawdown: Optional[Tuple[float, float, float]] = None
    for ts, value in valid:
        if peak is None or value > peak[1]:
            peak = (ts, value)
        if peak and peak[1] > 0:
            drawdown = (value / peak[1] - 1) * 100
            if max_drawdown is None or drawdown < max_drawdown[0]:
                max_drawdown = (drawdown, peak[0], ts)
    close_series = quality == "historical_close"
    true_intraday = quality in {"real_intraday", "cached_intraday", "stale_intraday"}
    checkpoint = quality == "performance_checkpoint"
    broad_trend = len(valid) >= (40 if str(timeframe).upper() == "6M" else 10) and (close_series or true_intraday)
    statistics = None
    if valid:
        statistics = {
            "start_at": _iso(valid[0][0]), "end_at": _iso(valid[-1][0]),
            "start_price": valid[0][1], "end_price": valid[-1][1],
            "return_pct": ((valid[-1][1] / valid[0][1]) - 1) * 100 if valid[0][1] else None,
            "low": min(value for _, value in valid), "high": max(value for _, value in valid),
            "max_drawdown_pct": max_drawdown[0] if max_drawdown else None,
            "max_drawdown_peak_at": _iso(max_drawdown[1]) if max_drawdown else None,
            "max_drawdown_trough_at": _iso(max_drawdown[2]) if max_drawdown else None,
        }
    return {
        "series_kind": "daily_close" if close_series else "intraday_price" if true_intraday else "performance_checkpoint" if checkpoint else "unknown",
        "timestamp_basis": timestamp_basis, "statistics": statistics,
        "supported_analysis": {"broad_trend": broad_trend, "close_to_close_momentum": close_series and len(valid) >= 20,
                               "observed_range": len(valid) >= 2, "drawdown": len(valid) >= 2,
                               "approximate_price_zones": close_series and len(valid) >= 60},
        "unsupported_analysis": {"exact_support_resistance": True, "candlestick_patterns": True,
                                 "volume_confirmation": True,
                                 "intraday_execution_levels": not true_intraday or len(valid) < 30},
        "required_language": ("Describe only provider performance checkpoints; do not call this a continuous historical chart."
                              if checkpoint else "Use broad trend, range, momentum, and drawdown language. Any price zone is approximate; exact technical levels require OHLCV candles."
                              if close_series else "State the limited series quality and avoid precise technical conclusions."),
    }


class CockpitStore:
    """Thread-safe loader for local contracts or their published live copies."""

    def __init__(self, data_dir: Optional[os.PathLike] = None) -> None:
        default_dir = Path(__file__).resolve().parents[1]
        self.data_dir = Path(data_dir or os.getenv("COCKPIT_DATA_DIR") or default_dir).resolve()
        self.base_url = str(os.getenv("COCKPIT_DATA_BASE_URL") or "").strip().rstrip("/")
        try:
            self.remote_cache_seconds = max(5, int(os.getenv("COCKPIT_REMOTE_CACHE_SECONDS", "30")))
        except ValueError:
            self.remote_cache_seconds = 30
        self._lock = threading.RLock()
        self._cache: Dict[str, Tuple[Tuple[int, int], Dict[str, Any]]] = {}
        self._remote_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._remote_errors: Dict[str, str] = {}

    def load(self, filename: str) -> Dict[str, Any]:
        if filename not in CONTRACT_FILES:
            raise RuntimeError("Unsupported Cockpit contract: %s" % filename)
        if self.base_url:
            return self._load_remote(filename)
        return self._load_local(filename)

    def _load_local(self, filename: str) -> Dict[str, Any]:
        path = self.data_dir / filename
        try:
            stat = path.stat()
        except FileNotFoundError as exc:
            raise RuntimeError("Missing Cockpit contract: %s" % path) from exc
        signature = (stat.st_mtime_ns, stat.st_size)
        with self._lock:
            cached = self._cache.get(filename)
            if cached and cached[0] == signature:
                return cached[1]
            try:
                with path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError("Invalid Cockpit contract: %s" % path) from exc
            if not isinstance(payload, dict):
                raise RuntimeError("Cockpit contract must be a JSON object: %s" % path)
            self._cache[filename] = (signature, payload)
            return payload

    @staticmethod
    def _validate_payload(filename: str, payload: Any) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise RuntimeError("Cockpit contract must be a JSON object: %s" % filename)
        return payload

    def _load_remote(self, filename: str) -> Dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            cached = self._remote_cache.get(filename)
            if cached and now - cached[0] < self.remote_cache_seconds:
                return cached[1]

        url = "%s/%s" % (self.base_url, filename)
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "project-cockpit-mcp/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                raw = response.read(MAX_CONTRACT_BYTES + 1)
            if len(raw) > MAX_CONTRACT_BYTES:
                raise RuntimeError("Remote Cockpit contract exceeds 32 MB: %s" % filename)
            payload = self._validate_payload(filename, json.loads(raw.decode("utf-8")))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, urllib.error.URLError, RuntimeError) as exc:
            message = "%s: %s" % (exc.__class__.__name__, _clean_text(exc))
            with self._lock:
                self._remote_errors[filename] = message
                cached = self._remote_cache.get(filename)
                if cached:
                    return cached[1]
            try:
                return self._load_local(filename)
            except RuntimeError as local_exc:
                raise RuntimeError("Unable to load remote Cockpit contract %s" % url) from local_exc

        with self._lock:
            self._remote_cache[filename] = (now, payload)
            self._remote_errors.pop(filename, None)
        return payload

    def health(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "contract_source": self.base_url or str(self.data_dir),
                "source_mode": "remote_live" if self.base_url else "local_files",
                "remote_cache_seconds": self.remote_cache_seconds if self.base_url else None,
                "last_fetch_errors": dict(self._remote_errors),
            }

    def snapshot(self) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        data = self.load("data.json")
        scores = self.load("scores.json").get("scores", {})
        charts = self.load("charts.json").get("charts", {})
        return data, scores, charts


class CockpitService:
    """High-signal, bounded queries over Cockpit market and intelligence data."""

    def __init__(self, data_dir: Optional[os.PathLike] = None) -> None:
        self.store = CockpitStore(data_dir)
        self._index_signature: Optional[Tuple[str, int, int]] = None
        self._assets: List[Dict[str, Any]] = []
        self._by_ticker: Dict[str, List[Dict[str, Any]]] = {}
        self._by_ref: Dict[str, Dict[str, Any]] = {}

    def _refresh_assets(self, data: Dict[str, Any], scores: Dict[str, Any], charts: Dict[str, Any]) -> None:
        signature = (str(data.get("timestamp")), len(scores), len(charts))
        if signature == self._index_signature:
            return
        assets: List[Dict[str, Any]] = []
        seen = set()
        for sector in data.get("sectors") or []:
            sector_key = sector.get("key")
            sector_name = sector.get("name")
            for original in sector.get("constituents") or []:
                row = dict(original)
                row.setdefault("sector_key", sector_key)
                row.setdefault("sector_name", sector_name)
                ref = row.get("score_ref") or row.get("chart_ref") or "%s|%s|%s" % (
                    row.get("country"), row.get("ticker"), sector_key
                )
                if ref in seen:
                    continue
                seen.add(ref)
                row["_ref"] = ref
                row["_score"] = scores.get(row.get("score_ref") or ref) or row.get("fundamental_score") or {}
                row["_chart"] = charts.get(row.get("chart_ref") or ref) or {}
                assets.append(row)
        by_ticker: Dict[str, List[Dict[str, Any]]] = {}
        for row in assets:
            keys = {str(row.get("ticker") or "").upper(), str(row.get("source_symbol") or "").upper()}
            for key in keys:
                if key:
                    by_ticker.setdefault(key, []).append(row)
                    if key.endswith(".JK"):
                        by_ticker.setdefault(key[:-3], []).append(row)
        self._assets = assets
        self._by_ticker = by_ticker
        self._by_ref = {str(row.get("_ref")): row for row in assets}
        self._index_signature = signature

    def _snapshot(self) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        data, scores, charts = self.store.snapshot()
        self._refresh_assets(data, scores, charts)
        return data, scores, charts

    @staticmethod
    def _score_summary(score: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not score or score.get("score") is None:
            return None
        return {
            "score": score.get("score"),
            "label": score.get("label"),
            "mode": score.get("mode"),
            "confidence": score.get("confidence"),
            "data_confidence_pct": score.get("data_confidence_pct"),
            "data_confidence_components": score.get("data_confidence_components"),
            "methodology": score.get("score_methodology"),
            "coverage": score.get("input_coverage", score.get("coverage")),
            "axes": score.get("axes") or [],
            "as_of": score.get("as_of"),
            "source": score.get("source"),
            "warnings": score.get("data_warnings") or [],
            "limitations": score.get("limitations") or [],
        }

    def _asset_view(self, row: Dict[str, Any]) -> Dict[str, Any]:
        score = row.get("_score") or {}
        return {
            "ticker": row.get("ticker"),
            "name": row.get("name"),
            "source_symbol": row.get("source_symbol"),
            "country": row.get("country"),
            "country_name": row.get("country_name"),
            "exchange": row.get("exchange"),
            "sector": row.get("sector_key"),
            "industry": row.get("industry"),
            "price": row.get("value"),
            "return_24h_pct": row.get("delta_pct"),
            "market_cap": row.get("market_cap_value"),
            "market_cap_display": row.get("mktcap"),
            "market_state": row.get("state"),
            "quote_as_of": _iso(row.get("quote_asof")),
            "quote_mode": row.get("quote_mode"),
            "source": {
                "name": row.get("source_name") or row.get("source_provider"),
                "url": row.get("source_url") or row.get("url"),
            },
            "chart_quality": row.get("chart_quality") or {},
            "score": self._score_summary(score),
            "data_tier": row.get("data_tier"),
            "reference": row.get("_ref"),
        }

    def _resolve(self, ticker: str, country: str = "") -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        self._snapshot()
        key = str(ticker or "").strip().upper()
        candidates = list(self._by_ticker.get(key, []))
        market = _market_code(country) if country else "ALL"
        if market != "ALL":
            candidates = [row for row in candidates if row.get("country") == market or row.get("region") == market]
        unique = {row.get("_ref"): row for row in candidates}
        candidates = list(unique.values())
        if len(candidates) == 1:
            return candidates[0], candidates
        if len(candidates) > 1:
            candidates.sort(key=lambda row: (row.get("country") != "ID", -(row.get("market_cap_value") or 0)))
        return None, candidates

    def status(self) -> Dict[str, Any]:
        data, scores, charts = self._snapshot()
        health = data.get("intelligence_health") or {}
        source_health = (data.get("coverage_universe") or {}).get("source_health") or {}
        return {
            "service": "Project Cockpit MCP",
            "mode": "read_only",
            "payload_timestamp": data.get("timestamp"),
            "generated_by": data.get("generated_by"),
            "asset_count": len(self._assets),
            "score_count": len(scores),
            "chart_count": len(charts),
            "news_count": len(data.get("news") or []),
            "video_count": len(data.get("videos") or []),
            "knowledge_count": len(data.get("podcasts") or []),
            "research_count": len((data.get("research") or {}).get("reports") or []),
            "source_health": source_health,
            "intelligence_health": health,
            "contracts": ["data.json", "scores.json", "charts.json"],
            "contract_health": self.store.health(),
        }

    def market_telemetry(self, symbol: str = "", include_chart: bool = False) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        wanted = str(symbol or "").strip().upper()
        results = []
        for item in data.get("telemetry") or []:
            if wanted and wanted not in {str(item.get("symbol") or "").upper(), str(item.get("label") or "").upper()}:
                continue
            row = {
                "symbol": item.get("symbol"), "label": item.get("label"), "kind": item.get("kind"),
                "region": item.get("region"), "country_code": item.get("country_code"),
                "value": item.get("value"), "value_unit": item.get("value_unit"),
                "return_24h_pct": item.get("delta_pct"), "previous_close": item.get("prev_close"),
                "market_state": item.get("state"), "quote_as_of": _iso(item.get("quote_asof")),
                "quote_mode": item.get("quote_mode"), "chart_quality": item.get("chart_quality") or {},
                "source_url": item.get("url"),
            }
            if include_chart:
                row["chart"] = {
                    "historical": [{"timestamp": _iso(ts), "value": value}
                                   for ts, value in zip(item.get("spark_ts") or [], item.get("spark") or [])],
                    "intraday": item.get("intraday") or [],
                }
            results.append(row)
        return {"as_of": data.get("timestamp"), "symbol": symbol or None, "results": results}

    def macro_indicators(self, view: str = "core", pillar: str = "") -> Dict[str, Any]:
        """Return source-linked official Indonesia macro releases."""
        data, _, _ = self._snapshot()
        macro = data.get("macro_indicators") or {}
        aliases = {"indonesia": "core", "indonesia_core": "core",
                   "overview": "core", "headline": "core", "indonesia_detail": "detail",
                   "rating": "ratings", "credit_ratings": "ratings",
                   "market_classification": "ratings", "risk": "country_risk",
                   "countryrisk": "country_risk", "risk_premium": "country_risk"}
        key = aliases.get(_norm(view).replace(" ", "_"), _norm(view).replace(" ", "_")) or "core"
        if key not in {"core", "detail", "ratings", "country_risk"}:
            return {"status": "invalid_view", "allowed": ["core", "detail", "ratings", "country_risk"]}
        rows = list(macro.get(key) or [])
        if pillar:
            wanted = _norm(pillar)
            rows = [item for item in rows if wanted in _norm(item.get("pillar"))]
        return {
            "status": "ok", "as_of": data.get("timestamp"), "data_cutoff": macro.get("data_cutoff"),
            "view": key, "pillar": pillar or None, "results": rows,
            "health": macro.get("health") or {}, "refresh_policy": macro.get("refresh_policy"),
            "methodology_note": (macro.get("country_risk_note") if key == "country_risk"
                                 else macro.get("methodology_note")),
        }

    def heatmap(self, market: str = "id", sector: str = "", limit: int = 120) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        raw_market = _norm(market).replace(" ", "")
        code = _market_code(market)
        wanted_sector = _norm(sector).replace(" ", "_")
        rows = []
        for row in self._assets:
            groups = {str(value).lower().replace(" ", "") for value in row.get("index_groups") or []}
            if raw_market in ("sp500", "s&p500", "s&p_500"):
                if not any("sp500" in group or "s&p500" in group for group in groups):
                    continue
            elif raw_market in ("nasdaq100", "nasdaq_100"):
                if not any("nasdaq100" in group for group in groups):
                    continue
            elif code == "OTHERS":
                if row.get("region") != "OTHERS":
                    continue
            elif code != "ALL" and row.get("country") != code and row.get("region") != code:
                continue
            if wanted_sector and wanted_sector != _norm(row.get("sector_key")).replace(" ", "_"):
                continue
            if _finite(row.get("value")) is None:
                continue
            rows.append(row)
        rows.sort(key=lambda row: (-(row.get("market_cap_value") or 0), str(row.get("ticker"))))
        capped = rows[:_clamp_limit(limit, 120, 500)]
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for row in capped:
            groups.setdefault(str(row.get("sector_key") or "other"), []).append(self._asset_view(row))
        return {
            "as_of": data.get("timestamp"), "market": market, "sector": sector or None,
            "size_metric": "market_cap", "color_metric": "return_24h_pct", "total_matches": len(rows),
            "results": [self._asset_view(row) for row in capped], "by_sector": groups,
        }

    def trending(self, market: str = "all", mode: str = "all") -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        payload = data.get("trending") or {}
        market_key = str(market or "all").lower()
        mode_key = str(mode or "all").lower()
        if market_key == "all":
            result = payload
        else:
            result = payload.get(market_key) or {}
            if mode_key != "all" and isinstance(result, dict):
                result = result.get(mode_key) or []
        return {"as_of": data.get("timestamp"), "market": market_key, "mode": mode_key, "results": result}

    def search_assets(
        self, query: str = "", market: str = "all", sector: str = "", limit: int = 15
    ) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        market_code = _market_code(market)
        wanted_sector = _norm(sector).replace(" ", "_")
        query_tokens = _tokens(query)
        ranked = []
        for row in self._assets:
            if market_code not in ("ALL", "OTHERS") and row.get("country") != market_code and row.get("region") != market_code:
                continue
            if market_code == "OTHERS" and row.get("region") != "OTHERS":
                continue
            if wanted_sector and wanted_sector not in {_norm(row.get("sector_key")).replace(" ", "_"), _norm(row.get("sector_name")).replace(" ", "_")}:
                continue
            haystack = _norm(" ".join(str(row.get(key) or "") for key in ("ticker", "source_symbol", "name", "industry", "sector_key", "country_name")))
            if query_tokens and not all(token in haystack for token in query_tokens):
                continue
            exact = 1 if _norm(query) in {_norm(row.get("ticker")), _norm(row.get("source_symbol"))} else 0
            prefix = 1 if _norm(row.get("ticker")).startswith(_norm(query)) else 0
            ranked.append((exact, prefix, row.get("market_cap_value") or 0, row))
        ranked.sort(key=lambda item: (-item[0], -item[1], -item[2], str(item[3].get("ticker"))))
        cap = _clamp_limit(limit, 15, 50)
        return {
            "as_of": data.get("timestamp"),
            "query": query,
            "market": market_code,
            "sector": sector or None,
            "total_matches": len(ranked),
            "results": [self._asset_view(item[3]) for item in ranked[:cap]],
        }

    def get_asset(self, ticker: str, country: str = "") -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        row, candidates = self._resolve(ticker, country)
        if row is None:
            if candidates:
                return {
                    "status": "ambiguous",
                    "message": "Specify country because this ticker has multiple matches.",
                    "candidates": [self._asset_view(item) for item in candidates[:10]],
                }
            suggestions = self.search_assets(ticker, country or "all", limit=5).get("results", [])
            return {"status": "not_found", "ticker": ticker, "suggestions": suggestions}
        result = self._asset_view(row)
        result.update({
            "status": "ok",
            "payload_timestamp": data.get("timestamp"),
            "performance": {
                "1W": row.get("perf_1w"), "1M": row.get("perf_1m"), "3M": row.get("perf_3m"),
                "6M": row.get("perf_6m"), "YTD": row.get("perf_ytd"), "1Y": row.get("perf_1y"),
            },
            "liquidity": {
                "volume": row.get("volume"), "avg_volume_10d": row.get("avg_volume_10d"),
                "avg_volume_30d": row.get("avg_volume_30d"), "relative_volume_10d": row.get("relative_volume_10d"),
                "turnover": row.get("turnover"),
            },
            "technicals": {"rsi": row.get("rsi"), "tradingview_rating": row.get("recommend_all")},
            "analyst_targets": {
                "low": row.get("analyst_target_low"), "median": row.get("analyst_target_median"),
                "high": row.get("analyst_target_high"),
            },
        })
        return result

    def get_chart(self, ticker: str, timeframe: str = "1M", country: str = "") -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        row, candidates = self._resolve(ticker, country)
        if row is None:
            return {"status": "ambiguous" if candidates else "not_found", "ticker": ticker,
                    "candidates": [self._asset_view(item) for item in candidates[:10]]}
        frame = str(timeframe or "1M").upper()
        if frame not in ("24H", "1W", "1M", "3M", "6M"):
            return {"status": "invalid_timeframe", "allowed": ["24h", "1W", "1M", "3M", "6M"]}
        chart = row.get("_chart") or {}
        quality = (row.get("chart_quality") or {}).get("24h" if frame == "24H" else frame)
        points: List[Dict[str, Any]] = []
        timestamp_basis = "provider_timestamps"
        if frame == "24H":
            values = chart.get("intraday") or row.get("intraday") or []
            timestamps = chart.get("intraday_ts") or row.get("intraday_ts") or []
            end_ts = (_finite(row.get("chart_asof")) or _finite(row.get("quote_asof"))
                      or datetime.now(tz=timezone.utc).timestamp())
            step = max(60, int(86400 / max(1, len(values) - 1)))
            timestamp_basis = "provider_timestamps" if timestamps else "estimated_even_spacing_from_quote_time"
            for index, value in enumerate(values):
                ts = timestamps[index] if index < len(timestamps) else end_ts - step * (len(values) - 1 - index)
                points.append({"timestamp": _iso(ts), "value": value})
        else:
            values = chart.get("spark") or []
            timestamps = chart.get("spark_ts") or []
            cutoff_days = TIMEFRAME_DAYS[frame]
            if timestamps:
                max_ts = max(_finite(ts) or 0 for ts in timestamps)
                cutoff = max_ts - cutoff_days * 86400
                points = [{"timestamp": _iso(ts), "value": value} for ts, value in zip(timestamps, values)
                          if (_finite(ts) or 0) >= cutoff]
            else:
                points = [{"timestamp": None, "value": value} for value in values]
        return {
            "status": "ok" if points else "unavailable",
            "payload_timestamp": data.get("timestamp"),
            "ticker": row.get("ticker"),
            "country": row.get("country"),
            "timeframe": "24h" if frame == "24H" else frame,
            "chart_quality": quality or "unavailable",
            "point_count": len(points),
            "points": points,
            "analysis_guardrails": _chart_assessment(points, quality or "unavailable", frame, timestamp_basis),
            "source": {"name": row.get("source_name") or row.get("source_provider"),
                       "url": row.get("source_url") or row.get("url")},
            "note": "Use these returned points instead of scraping the dashboard UI. Interactive provider charts are a visual fallback, not a substitute data source.",
        }

    def get_score(self, ticker: str, country: str = "") -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        row, candidates = self._resolve(ticker, country)
        if row is None:
            return {"status": "ambiguous" if candidates else "not_found", "ticker": ticker,
                    "candidates": [self._asset_view(item) for item in candidates[:10]]}
        score = row.get("_score") or {}
        if not score:
            return {"status": "unavailable", "ticker": row.get("ticker"), "reason": "No validated score payload."}
        result = dict(score)
        result.update({
            "status": "ok", "ticker": row.get("ticker"), "name": row.get("name"),
            "country": row.get("country"), "sector": row.get("sector_key"),
            "payload_timestamp": data.get("timestamp"),
            "source_url": row.get("source_url") or row.get("url"),
        })
        return result

    def compare_assets(self, tickers: Sequence[str], country: str = "") -> Dict[str, Any]:
        items = []
        for ticker in list(tickers or [])[:12]:
            asset = self.get_asset(str(ticker), country)
            if asset.get("status") == "ok":
                score_detail = self.get_score(str(ticker), country)
                items.append({
                    "asset": asset,
                    "valuation": score_detail.get("valuation") if score_detail.get("status") == "ok" else None,
                    "risk": score_detail.get("risk_stats") if score_detail.get("status") == "ok" else None,
                })
            else:
                items.append(asset)
        return {"count": len(items), "results": items}

    def list_sectors(self) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        sectors = []
        for sector in data.get("sectors") or []:
            sectors.append({
                "key": sector.get("key"), "name": sector.get("name"), "signal": sector.get("signal"),
                "return_pct": sector.get("change"), "indonesia_return_pct": sector.get("idChange"),
                "us_return_pct": sector.get("usChange"), "constituent_count": len(sector.get("constituents") or []),
            })
        return {"as_of": data.get("timestamp"), "sectors": sectors}

    def get_sector(self, sector: str, market: str = "all", limit: int = 20) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        wanted = _norm(sector).replace(" ", "_")
        match = next((item for item in data.get("sectors") or []
                      if wanted in {_norm(item.get("key")).replace(" ", "_"), _norm(item.get("name")).replace(" ", "_")}), None)
        if not match:
            return {"status": "not_found", "sector": sector, "available": [item.get("key") for item in data.get("sectors") or []]}
        code = _market_code(market)
        rows = [row for row in match.get("constituents") or []
                if code == "ALL" or row.get("country") == code or row.get("region") == code]
        rows.sort(key=lambda row: (-(row.get("market_cap_value") or 0), str(row.get("ticker"))))
        return {
            "status": "ok", "as_of": data.get("timestamp"), "key": match.get("key"), "name": match.get("name"),
            "signal": match.get("signal"), "return_pct": match.get("change"),
            "regional_returns": {"indonesia": match.get("idChange"), "us": match.get("usChange")},
            "structural_themes": match.get("themes") or [], "actionable_intelligence": _clean_text(match.get("ai")),
            "total_constituents": len(rows),
            "constituents": [self._asset_view(self._by_ref.get(str(row.get("score_ref") or row.get("chart_ref")))
                                               or dict(row, _score=(row.get("fundamental_score") or {}),
                                                       _ref=row.get("score_ref") or row.get("chart_ref")))
                             for row in rows[:_clamp_limit(limit, 20, 50)]],
        }

    @staticmethod
    def _axis(score: Dict[str, Any], key: str) -> Optional[float]:
        for axis in score.get("axes") or []:
            if axis.get("key") == key:
                return _finite(axis.get("score"))
        return None

    def _risk_price_score(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        score = row.get("_score") or {}
        total = _finite(score.get("score"))
        if total is None:
            return None
        risk = self._axis(score, "risk") or total
        momentum = self._axis(score, "momentum") or 50
        value = self._axis(score, "value") or total
        quality = self._axis(score, "quality") or total
        valuation = score.get("valuation") or {}
        upside = _finite(valuation.get("upside_pct"))
        mode = str(score.get("mode") or "equity").lower()
        if mode != "crypto" and upside is None:
            return None
        stats = score.get("risk_stats") or {}
        sharpe = _finite(stats.get("sharpe"))
        sortino = _finite(stats.get("sortino"))
        drawdown = _finite(stats.get("max_drawdown_pct"))
        clamp = lambda value: max(0.0, min(100.0, value))
        sharpe_score = risk if sharpe is None else clamp((sharpe + 0.25) / 1.75 * 100)
        sortino_score = sharpe_score if sortino is None else clamp((sortino + 0.25) / 2.25 * 100)
        risk_adjusted = (sharpe_score + sortino_score) / 2
        drawdown_score = risk if drawdown is None else clamp((45 - abs(drawdown)) / 45 * 100)
        valuation_score = value if upside is None else clamp((upside + 20) / 60 * 100)
        if mode == "crypto":
            result = total * .35 + risk * .20 + risk_adjusted * .20 + momentum * .15 + drawdown_score * .10
        else:
            result = value * .25 + quality * .25 + valuation_score * .20 + risk_adjusted * .15 + drawdown_score * .10 + momentum * .05
        return {"score": round(clamp(result), 2), "upside_pct": upside}

    def market_movers(self, market: str = "id", mode: str = "gainers", limit: int = 8) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        code = _market_code(market)
        rows = [row for row in self._assets if code == "ALL" or row.get("country") == code or row.get("region") == code]
        mode = str(mode or "gainers").lower()
        if mode == "top_score":
            rows = [row for row in rows if _finite((row.get("_score") or {}).get("score")) is not None]
            rows.sort(key=lambda row: (-(_finite((row.get("_score") or {}).get("score")) or 0), -(_finite(row.get("delta_pct")) or 0)))
        elif mode in ("best_risk_price", "best_value"):
            ranked = [(self._risk_price_score(row), row) for row in rows]
            ranked = [(score, row) for score, row in ranked if score]
            ranked.sort(key=lambda item: -item[0]["score"])
            rows = [row for _, row in ranked]
        else:
            rows = [row for row in rows if _finite(row.get("delta_pct")) is not None]
            rows.sort(key=lambda row: _finite(row.get("delta_pct")) or 0, reverse=mode != "losers")
        results = []
        for row in rows[:_clamp_limit(limit, 8, 50)]:
            item = self._asset_view(row)
            risk_price = self._risk_price_score(row)
            if risk_price:
                item["risk_price"] = risk_price
            results.append(item)
        return {"as_of": data.get("timestamp"), "market": code, "mode": mode, "results": results}

    def _must_read_keys(self, data: Dict[str, Any]) -> Tuple[set, set]:
        urls, titles = set(), set()
        for wrapper in (data.get("daily_brief") or {}).get("must_read") or []:
            item = wrapper.get("news") if isinstance(wrapper, dict) else None
            if not isinstance(item, dict):
                continue
            if item.get("url"):
                urls.add(item["url"])
            titles.add(_title_key(item.get("title")))
        return urls, titles

    def search_news(
        self, query: str = "", market: str = "all", category: str = "", sector: str = "",
        ticker: str = "", window_days: int = 7, must_read_only: bool = False, limit: int = 15,
    ) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        items: Iterable[Dict[str, Any]] = data.get("news") or []
        if ticker:
            items = (data.get("ticker_news") or {}).get(str(ticker).upper()) or []
        code = _market_code(market)
        wanted_category = _norm(category).replace(" ", "_")
        wanted_sector = _norm(sector).replace(" ", "_")
        query_tokens = _tokens(query)
        must_urls, must_titles = self._must_read_keys(data)
        anchor = _finite(max((item.get("ts") or 0 for item in items), default=0)) or datetime.now(tz=timezone.utc).timestamp()
        cutoff = anchor - max(1, min(7, int(window_days or 7))) * 86400
        ranked = []
        seen = set()
        for item in items:
            identity = item.get("url") or _title_key(item.get("title"))
            if not identity or identity in seen:
                continue
            seen.add(identity)
            is_must = item.get("url") in must_urls or _title_key(item.get("title")) in must_titles
            if must_read_only and not is_must:
                continue
            if (_finite(item.get("ts")) or 0) < cutoff:
                continue
            if code != "ALL" and item.get("geo") != code:
                continue
            if wanted_category and wanted_category != _norm(item.get("category")).replace(" ", "_"):
                continue
            item_sectors = {_norm(value).replace(" ", "_") for value in item.get("sectors") or []}
            if wanted_sector and wanted_sector not in item_sectors:
                continue
            haystack = _norm(" ".join(str(item.get(key) or "") for key in ("title", "summary", "source", "query")))
            if query_tokens and not all(token in haystack for token in query_tokens):
                continue
            rank = (10000 if is_must else 0) + int(item.get("score") or 0) + int((_finite(item.get("ts")) or 0) / 1000000)
            ranked.append((rank, item, is_must))
        ranked.sort(key=lambda value: (-value[0], -(_finite(value[1].get("ts")) or 0)))
        return {
            "as_of": data.get("timestamp"), "query": query, "market": code, "category": category or None,
            "sector": sector or None, "ticker": ticker or None, "window_days": max(1, min(7, int(window_days or 7))),
            "total_matches": len(ranked),
            "results": [_public_news(item, is_must) for _, item, is_must in ranked[:_clamp_limit(limit, 15, 50)]],
            "grounding_note": "Items without a stored summary are headline-and-metadata evidence only.",
        }

    def _must_watch_ids(self, data: Dict[str, Any]) -> set:
        result = set()
        for wrapper in (data.get("daily_brief") or {}).get("must_watch") or []:
            item = wrapper.get("video") if isinstance(wrapper, dict) else None
            if isinstance(item, dict) and item.get("video_id"):
                result.add(item["video_id"])
        return result

    def get_news(self, url_or_title: str) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        wanted = str(url_or_title or "").strip()
        wanted_title = _title_key(wanted)
        must_urls, must_titles = self._must_read_keys(data)
        pool: List[Dict[str, Any]] = list(data.get("news") or [])
        for items in (data.get("ticker_news") or {}).values():
            pool.extend(items or [])
        seen = set()
        for item in pool:
            identity = item.get("url") or _title_key(item.get("title"))
            if not identity or identity in seen:
                continue
            seen.add(identity)
            if item.get("url") == wanted or _title_key(item.get("title")) == wanted_title:
                is_must = item.get("url") in must_urls or _title_key(item.get("title")) in must_titles
                return {"status": "ok", "as_of": data.get("timestamp"), "news": _public_news(item, is_must)}
        suggestions = self.search_news(query=wanted, limit=5).get("results") or []
        return {"status": "not_found", "query": wanted, "suggestions": suggestions}

    def search_videos(
        self, query: str = "", market: str = "all", category: str = "", channel: str = "",
        window_days: int = 7, must_watch_only: bool = False, include_knowledge: bool = False, limit: int = 15,
    ) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        items = [dict(item, _collection="intelligence_hub") for item in data.get("videos") or []]
        if include_knowledge:
            items.extend(dict(item, _collection="knowledge_hub", channel=item.get("show"), summary=item.get("thesis"))
                         for item in data.get("podcasts") or [])
        code = _market_code(market)
        wanted_category = _norm(category).replace(" ", "_")
        wanted_channel = _norm(channel)
        query_tokens = _tokens(query)
        must_ids = self._must_watch_ids(data)
        anchor = max((_finite(item.get("ts")) or 0 for item in items), default=datetime.now(tz=timezone.utc).timestamp())
        cutoff = anchor - max(1, min(7, int(window_days or 7))) * 86400
        ranked = []
        seen = set()
        for item in items:
            video_id = item.get("video_id") or item.get("url")
            if not video_id or video_id in seen:
                continue
            seen.add(video_id)
            is_must = item.get("video_id") in must_ids
            if must_watch_only and not is_must:
                continue
            if (_finite(item.get("ts")) or 0) < cutoff:
                continue
            if code != "ALL" and item.get("geo") != code:
                continue
            if wanted_category and wanted_category != _norm(item.get("category")).replace(" ", "_"):
                continue
            if wanted_channel and wanted_channel not in _norm(item.get("channel") or item.get("show")):
                continue
            haystack = _norm(" ".join(str(item.get(key) or "") for key in ("title", "summary", "thesis", "channel", "show", "category")))
            if query_tokens and not all(token in haystack for token in query_tokens):
                continue
            ranked.append((10000 if is_must else 0, _finite(item.get("ts")) or 0, item, is_must))
        ranked.sort(key=lambda value: (-value[0], -value[1]))
        return {
            "as_of": data.get("timestamp"), "query": query, "market": code, "category": category or None,
            "channel": channel or None, "window_days": max(1, min(7, int(window_days or 7))),
            "include_knowledge": include_knowledge, "total_matches": len(ranked),
            "results": [_public_video(item, is_must) for _, _, item, is_must in ranked[:_clamp_limit(limit, 15, 50)]],
            "grounding_note": "Stored summaries are used when present; otherwise only title and metadata are returned.",
        }

    def get_video(self, video_id: str) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        must_ids = self._must_watch_ids(data)
        for collection, items in (("intelligence_hub", data.get("videos") or []), ("knowledge_hub", data.get("podcasts") or [])):
            for original in items:
                if original.get("video_id") == video_id or original.get("url") == video_id:
                    item = dict(original, _collection=collection)
                    if collection == "knowledge_hub":
                        item.update(channel=item.get("show"), summary=item.get("thesis"))
                    return {"status": "ok", "as_of": data.get("timestamp"),
                            "video": _public_video(item, item.get("video_id") in must_ids)}
        return {"status": "not_found", "video_id": video_id}

    def knowledge_hub(self, category: str = "all", query: str = "", limit: int = 20) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        wanted = _norm(category).replace(" ", "_")
        query_tokens = _tokens(query)
        rows = []
        for item in data.get("podcasts") or []:
            if wanted not in ("", "all") and wanted != _norm(item.get("category")).replace(" ", "_"):
                continue
            haystack = _norm(" ".join(str(item.get(key) or "") for key in ("title", "thesis", "show", "host")))
            if query_tokens and not all(token in haystack for token in query_tokens):
                continue
            rows.append(item)
        rows.sort(key=lambda item: -(_finite(item.get("ts")) or 0))
        return {"as_of": data.get("timestamp"), "category": category, "total_matches": len(rows),
                "results": [_public_video(dict(item, _collection="knowledge_hub", channel=item.get("show"), summary=item.get("thesis")))
                            for item in rows[:_clamp_limit(limit, 20, 50)]]}

    def search_research(
        self, query: str = "", category: str = "", geography: str = "", ticker: str = "",
        publisher: str = "", publishers: Optional[Sequence[str]] = None,
        date_from: str = "", date_to: str = "", year: Optional[int] = None,
        period: str = "", open_only: bool = False, limit: int = 20,
    ) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        query_tokens = _tokens(query)
        wanted_category = _norm(category)
        wanted_geography = _norm(geography)
        requested_publishers = list(dict.fromkeys(
            _clean_text(value) for value in ([publisher] + list(publishers or [])) if _clean_text(value)))
        wanted_publishers = [_norm(value) for value in requested_publishers]
        wanted_ticker = str(ticker or "").strip().upper()
        bounds = _research_date_bounds(date_from, date_to, year, period)
        priority_rank = {"essential": 0, "high": 1, "live": 2, "supplementary": 3}
        rows = []
        for item in (data.get("research") or {}).get("reports") or []:
            if wanted_category and wanted_category not in _norm(item.get("category")):
                continue
            if wanted_geography and wanted_geography not in _norm(item.get("geography")):
                continue
            item_publisher = _norm(item.get("publisher"))
            if wanted_publishers and not any(value in item_publisher or item_publisher in value
                                             for value in wanted_publishers):
                continue
            ticker_tags = {str(value).upper() for value in item.get("ticker_tags") or []}
            if wanted_ticker and wanted_ticker not in ticker_tags:
                continue
            if open_only and not ("open" in _norm(item.get("access")) or item.get("direct_url")):
                continue
            published_ts = _finite(item.get("published_ts")) or _parse_research_date(item.get("published")) or 0
            if bounds["from"] and published_ts < bounds["from"]:
                continue
            if bounds["to"] and published_ts > bounds["to"]:
                continue
            haystack = _norm(" ".join(str(value or "") for value in (
                item.get("title"), item.get("publisher"), item.get("category"), item.get("subcategory"),
                item.get("geography"), item.get("coverage"), item.get("why_useful"),
                " ".join(item.get("ticker_tags") or []), " ".join(item.get("sector_tags") or []),
            )))
            if query_tokens and not all(token in haystack for token in query_tokens):
                continue
            rows.append(item)
        rows.sort(key=lambda item: (
            priority_rank.get(_norm(item.get("priority")), 4),
            -(int(item.get("published_ts") or 0)),
            str(item.get("publisher") or ""), str(item.get("title") or ""),
        ))
        research = data.get("research") or {}
        return {
            "status": "ok", "as_of": data.get("timestamp"),
            "query": {"query": query, "category": category, "geography": geography,
                      "ticker": ticker, "publisher": publisher, "publishers": requested_publishers,
                      "date_from": date_from, "date_to": date_to, "year": year,
                      "period": period, "open_only": open_only},
            "period": bounds,
            "total_matches": len(rows),
            "results": [_public_research(item) for item in rows[:_clamp_limit(limit, 20, 50)]],
            "coverage_audit": _research_coverage(rows, requested_publishers),
            "synthesis": research.get("synthesis") or {}, "health": research.get("health") or {},
            "grounding_note": research.get("provenance_note"),
        }

    def research_synthesis(
        self, query: str = "", category: str = "", geography: str = "", ticker: str = "",
        publisher: str = "", publishers: Optional[Sequence[str]] = None,
        date_from: str = "", date_to: str = "", year: Optional[int] = None,
        period: str = "", open_only: bool = False, limit: int = 50,
    ) -> Dict[str, Any]:
        result = self.search_research(query, category, geography, ticker, publisher, publishers,
                                      date_from, date_to, year, period, open_only, min(50, limit or 50))
        reports = result.get("results") or []
        audit = result.get("coverage_audit") or {}
        return {
            "status": "ok" if reports else "insufficient_evidence", "as_of": result.get("as_of"),
            "request": result.get("query"), "period": result.get("period"),
            "reports": reports, "coverage_audit": audit,
            "synthesis_readiness": {
                "inventory_ready": bool(reports),
                "content_summary_ready": bool(audit.get("content_evidence_count")),
                "source_open_required": bool(audit.get("source_open_required_count")),
                "reason": ("At least one indexed record includes bounded content evidence."
                           if audit.get("content_evidence_count") else
                           "The index currently contains discovery metadata; open source_url before summarizing report conclusions."),
            },
            "required_output": [
                "Coverage audit: publishers found, missing publishers, dates, access, and evidence scope.",
                "Observed-period findings and forward outlook must be separated.",
                "Consensus, disagreements, Indonesia implications, and unresolved evidence gaps.",
                "Every report-level claim must cite source_url and be attributed to its publisher.",
            ],
            "routing_policy": {
                "first_source": "Project Cockpit research index",
                "external_search": "Use only to open indexed source_url records or fill publishers explicitly listed as missing.",
                "prohibition": "Do not replace this inventory with an unrelated generic research workflow or claim metadata is full-report content.",
            },
        }

    def get_research(self, id_or_url_or_title: str) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        wanted = str(id_or_url_or_title or "").strip()
        wanted_title = _title_key(wanted)
        for item in (data.get("research") or {}).get("reports") or []:
            if wanted in {item.get("id"), item.get("source_url"), item.get("direct_url"), item.get("landing_url")} \
                    or _title_key(item.get("title")) == wanted_title:
                return {"status": "ok", "as_of": data.get("timestamp"),
                        "research": _public_research(item),
                        "grounding_note": (data.get("research") or {}).get("provenance_note")}
        return {"status": "not_found", "query": wanted}

    def company_evidence(self, ticker: str, market: str = "id", window_days: int = 7) -> Dict[str, Any]:
        code = _market_code(market)
        asset = self.get_asset(ticker, market)
        score = self.get_score(ticker, market)
        chart = self.get_chart(ticker, "6M", market)
        news = self.search_news(ticker=ticker, market=market, window_days=window_days, limit=10)
        videos = self.search_videos(query=ticker, market=market, window_days=window_days,
                                    include_knowledge=True, limit=8)
        exact_research = self.search_research(ticker=ticker, limit=12)
        context = []
        if not exact_research.get("results"):
            geography = "Indonesia" if code == "ID" else "Global" if code == "US" else ""
            context = self.search_research(
                query=str(asset.get("sector") or "") if asset.get("status") == "ok" else "",
                geography=geography, limit=6,
            ).get("results") or []
            if not context and geography:
                context = self.search_research(geography=geography, limit=6).get("results") or []
        return {
            "ticker": str(ticker).upper(), "market": code,
            "asset": asset, "score": score, "chart": chart,
            "news": news.get("results") or [], "videos": videos.get("results") or [],
            "research": exact_research.get("results") or [], "context_research": context,
            "research_framework": {
                "evidence_layers": ["market data", "deterministic score", "company and sector news",
                                    "video intelligence", "institutional research"],
                "required_analysis": ["business and industry context", "earnings and catalysts", "valuation",
                                      "liquidity and risk", "bull/base/bear cases", "data gaps"],
                "mandatory_tool_sequence": ["get_company_evidence", "get_asset_chart", "get_asset_score",
                                            "search_news", "search_research"],
                "chart_policy": "Use MCP chart points first. Exact support/resistance, candlestick patterns, and volume confirmation require explicit OHLCV fields.",
            },
            "provenance_rules": [
                "Label provider facts, Cockpit calculations, publisher opinions, and AI inference separately.",
                "Broker opinions and target prices are evidence, not facts or personalized recommendations.",
                "Open the original report before relying on a recommendation, forecast, or valuation.",
                "Never inspect the dashboard UI for data exposed by an MCP tool.",
            ],
        }

    def daily_brief(self) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        brief = dict(data.get("daily_brief") or {})
        brief["payload_timestamp"] = data.get("timestamp")
        brief["provenance"] = "Cockpit's scheduled synthesis; source cards remain the evidence of record."
        return brief

    def market_sentiment(self) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        brief = data.get("daily_brief") or {}
        return {
            "as_of": data.get("timestamp"), "sentiment": brief.get("sentiment") or {},
            "daily_synthesis": brief.get("synthesis"), "key_themes": brief.get("key_themes") or [],
            "news_digest": brief.get("news_digest") or {}, "video_digest": brief.get("video_digest") or {},
        }

    def macro_analysis(self) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        return {"as_of": data.get("timestamp"), "analysis": data.get("macro_analysis") or [],
                "arbiter_brief": data.get("arbiter_brief"), "source_policy": "Each point carries its own source links."}

    def active_alerts(self) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        return {"as_of": data.get("timestamp"), "alerts": data.get("alerts") or []}

    def ipo_radar(self, view: str = "scheduled", market: str = "all", limit: int = 25) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        ipo = data.get("ipo") or {}
        view_key = str(view or "scheduled").lower().replace(" ", "_")
        aliases = {"recent": "recent", "recent_1y": "recent", "pipeline_filed": "pipeline", "filed": "pipeline"}
        view_key = aliases.get(view_key, view_key)
        if view_key not in ("scheduled", "pipeline", "recent", "sp500_changes"):
            return {"status": "invalid_view", "allowed": ["scheduled", "pipeline", "recent", "sp500_changes"]}
        code = _market_code(market)
        rows: List[Dict[str, Any]] = []
        if view_key == "sp500_changes":
            rows = list(ipo.get("sp500_changes") or [])
        else:
            if code in ("ALL", "ID"):
                rows.extend(ipo.get({"scheduled": "upcoming_id", "pipeline": "pipeline_id", "recent": "recent_id"}[view_key]) or [])
            if code in ("ALL", "US"):
                rows.extend(ipo.get({"scheduled": "upcoming_us", "pipeline": "pipeline_us", "recent": "recent_us"}[view_key]) or [])
        return {
            "status": "ok", "as_of": data.get("timestamp"), "view": view_key, "market": code,
            "total_matches": len(rows), "results": rows[:_clamp_limit(limit, 25, 50)],
            "synthesis": ipo.get("synthesis") or {}, "health": ipo.get("health") or {}, "note": ipo.get("note"),
        }

    def intelligence_brief(
        self, topic: str = "", ticker: str = "", sector: str = "", market: str = "all", window_days: int = 3,
    ) -> Dict[str, Any]:
        data, _, _ = self._snapshot()
        query = topic or ticker or sector
        asset = self.get_asset(ticker, market) if ticker else None
        news = self.search_news(query=query, market=market, sector=sector, ticker=ticker,
                                window_days=window_days, limit=8)
        videos = self.search_videos(query=query, market=market, window_days=window_days,
                                    include_knowledge=True, limit=8)
        research = self.search_research(query=query, ticker=ticker, limit=8)
        brief = data.get("daily_brief") or {}
        return {
            "as_of": data.get("timestamp"), "request": {"topic": topic, "ticker": ticker, "sector": sector,
                                                         "market": _market_code(market), "window_days": window_days},
            "asset": asset, "sentiment": brief.get("sentiment") or {},
            "daily_synthesis": brief.get("synthesis"), "key_themes": brief.get("key_themes") or [],
            "news": news.get("results") or [], "videos": videos.get("results") or [],
            "research": research.get("results") or [],
            "macro_indicators": self.macro_indicators("core"),
            "macro_analysis": data.get("macro_analysis") or [], "alerts": data.get("alerts") or [],
            "grounding_rules": [
                "Prefer exact ticker and source-linked evidence.",
                "Treat news without summaries as headline-only evidence.",
                "Treat video summaries as Cockpit synthesis, not a transcript, unless explicitly labelled otherwise.",
                "Treat broker and institutional research as attributed opinion and verify it at the source.",
                "State missing or stale data; never estimate absent fundamentals.",
            ],
        }

    def schema(self) -> Dict[str, Any]:
        return {
            "contracts": {
                "data.json": "market, sector, Intelligence Hub, Knowledge Hub, research, macro, alerts, and IPO summaries",
                "scores.json": "lazy-loaded deterministic scoring, valuation, metrics, and risk detail",
                "charts.json": "lazy-loaded historical and intraday chart points",
            },
            "source_of_truth": {
                "IDX_quotes": "TradingView snapshot with explicit fallback labels",
                "crypto": "CoinGecko",
                "fundamentals": "validated provider fields only",
                "reasoning": "scheduled DeepSeek synthesis where present",
                "scoring": "deterministic; never generated by DeepSeek",
            },
            "limits": {"max_tool_results": 50, "news_window_days": 7, "video_window_days": 7},
        }
