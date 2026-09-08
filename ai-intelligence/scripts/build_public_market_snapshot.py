#!/usr/bin/env python3
"""Create the compact public-market payload used by the AI World Map."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FIELDS = (
    "ticker", "source_symbol", "name", "exchange", "country_name", "sector_name", "industry",
    "value", "delta_pct", "mktcap", "market_cap_value", "volume", "turnover", "state",
    "quote_asof", "quote_mode", "perf_1w", "perf_1m", "perf_3m", "perf_6m", "perf_ytd",
    "perf_1y", "analyst_target_low", "analyst_target_median", "analyst_target_high", "rsi",
    "recommend_all", "fundamental_score", "source_name", "source_url", "market_data_warning",
)


def key(value: Any) -> str:
    return str(value or "").strip().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--cockpit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    profiles = json.loads(Path(args.profiles).read_text(encoding="utf-8"))
    cockpit = json.loads(Path(args.cockpit).read_text(encoding="utf-8"))
    rows = [row for sector in cockpit.get("sectors", []) for row in sector.get("constituents", [])]

    by_source: dict[str, dict[str, Any]] = {}
    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        source_symbol = key(row.get("source_symbol"))
        ticker = key(row.get("ticker"))
        if source_symbol:
            by_source[source_symbol] = row
        if ticker:
            by_ticker.setdefault(ticker, []).append(row)

    output: dict[str, dict[str, Any]] = {}
    unmatched: list[str] = []
    for profile in profiles.get("companies", []):
        market = profile.get("market") or {}
        if market.get("type") != "public":
            continue
        ticker = key(market.get("ticker"))
        row = by_source.get(ticker)
        if row is None:
            compact = ticker.split(".", 1)[0]
            candidates = by_ticker.get(compact, [])
            if len(candidates) == 1:
                row = candidates[0]
        if row is None:
            unmatched.append(profile.get("id") or ticker)
            continue
        compact_row = {field: row.get(field) for field in FIELDS if row.get(field) is not None}
        news_key = key(row.get("ticker"))
        news = (cockpit.get("ticker_news") or {}).get(news_key, [])[:5]
        compact_row["news"] = [
            {field: item.get(field) for field in ("title", "url", "source", "ts", "category") if item.get(field) is not None}
            for item in news
        ]
        output[str(profile.get("id"))] = compact_row

    payload = {
        "meta": {
            "generatedAt": cockpit.get("timestamp"),
            "source": "Project Cockpit",
            "matched": len(output),
            "publicProfiles": sum(1 for item in profiles.get("companies", []) if (item.get("market") or {}).get("type") == "public"),
            "unmatched": unmatched,
        },
        "companies": output,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(payload["meta"])


if __name__ == "__main__":
    main()
