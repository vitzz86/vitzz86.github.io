#!/usr/bin/env python3
"""Validate the core public URLs in the staged company database.

The check distinguishes syntactic completeness from network reachability.  A
401/403/429 response still proves that the host and resource route exist; it is
recorded as access-restricted rather than broken.  Redirect destinations are
retained so stale or renamed domains can be reviewed without silently changing
the workbook.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path
from urllib.parse import urlparse

import openpyxl
import requests


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36"
FIELDS = {
    "Companies DB": ("company_id", ["official_website", "company_linkedin", "logo_url", "company_x_url", "company_x_avatar_url"]),
    "Leadership DB": ("company_id", ["official_profile_url", "linkedin_url", "social_url", "photo_url", "x_url", "x_avatar_url"]),
    "Market Data": ("company_id", ["yahoo_finance_url", "investor_relations_url", "crunchbase_url"]),
}


def clean(value):
    return str(value or "").strip()


def is_http(value):
    try:
        parsed = urlparse(clean(value))
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def fetch(url, timeout=22):
    try:
        response = requests.get(
            url,
            headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )
        status = response.status_code
        final_url = response.url
        response.close()
        if 200 <= status < 400:
            classification = "reachable"
        # LinkedIn commonly returns the non-standard 999 anti-automation code
        # for valid public routes.  Treat it like 401/403 rather than a 404.
        elif status in {401, 403, 405, 429, 451, 999}:
            classification = "access_restricted"
        else:
            classification = "broken_http"
        return {"status": status, "final_url": final_url, "classification": classification}
    except Exception as exc:
        return {"status": 0, "final_url": url, "classification": "network_error", "error": type(exc).__name__}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=22)
    parser.add_argument("--only-field", action="append", default=[], help="Validate only these field names; may be repeated")
    args = parser.parse_args()

    workbook = openpyxl.load_workbook(args.input, read_only=True, data_only=True)
    records = []
    for sheet_name, (id_field, field_names) in FIELDS.items():
        sheet = workbook[sheet_name]
        headers = next(sheet.iter_rows(values_only=True))
        index = {value: position for position, value in enumerate(headers)}
        for row in sheet.iter_rows(min_row=2, values_only=True):
            company_id = clean(row[index[id_field]])
            for field in field_names:
                if args.only_field and field not in args.only_field:
                    continue
                value = clean(row[index[field]])
                if is_http(value):
                    records.append((sheet_name, company_id, field, value))

    unique_urls = sorted({record[3] for record in records})
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_url = {executor.submit(fetch, url, args.timeout): url for url in unique_urls}
        for number, future in enumerate(concurrent.futures.as_completed(future_to_url), 1):
            url = future_to_url[future]
            results[url] = future.result()
            if number % 100 == 0:
                print(f"validated {number}/{len(unique_urls)}", flush=True)

    by_field = {}
    failures = []
    for sheet_name, company_id, field, url in records:
        result = results[url]
        key = f"{sheet_name}.{field}"
        by_field.setdefault(key, {"total_urls": 0, "reachable": 0, "access_restricted": 0, "broken_http": 0, "network_error": 0})
        by_field[key]["total_urls"] += 1
        by_field[key][result["classification"]] += 1
        if result["classification"] in {"broken_http", "network_error"}:
            failures.append({"sheet": sheet_name, "company_id": company_id, "field": field, "url": url, **result})

    report = {
        "workbook": args.input,
        "unique_urls_checked": len(unique_urls),
        "by_field": by_field,
        "failures": failures,
    }
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({"output": args.output, "unique_urls_checked": len(unique_urls), "failures": len(failures)}, indent=2))


if __name__ == "__main__":
    main()
