#!/usr/bin/env python3
"""Strict, non-inflated completeness audit for the 497-company workbook.

Verified URL coverage and documented exceptions are reported separately.  A
placeholder never counts as a link, photo, market fact, or leadership profile.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import openpyxl


TODAY = dt.date.today()
URL = re.compile(r"^https?://", re.I)
EXCEPTION = re.compile(
    r"^(?:not applicable|no (?:verified|public|current|completed|qualifying)|"
    r"historical|initiative|research pending|amount not disclosed|"
    r"valuation not disclosed|date not disclosed)",
    re.I,
)


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def is_url(value) -> bool:
    return bool(URL.match(clean(value)))


def direct_linkedin_company(value) -> bool:
    text = clean(value).lower()
    return is_url(text) and "linkedin.com/" in text and any(p in text for p in ("/company/", "/showcase/"))


def direct_linkedin_person(value) -> bool:
    text = clean(value).lower()
    return is_url(text) and "linkedin.com/in/" in text


def direct_crunchbase(value) -> bool:
    try:
        parsed = urlparse(clean(value))
    except Exception:
        return False
    return parsed.netloc.lower().removeprefix("www.") == "crunchbase.com" and bool(
        re.fullmatch(r"/organization/[^/]+/?", parsed.path)
    )


def sheet_rows(workbook, sheet_name):
    sheet = workbook[sheet_name]
    header = [clean(cell.value) for cell in next(sheet.iter_rows())]
    return [dict(zip(header, (cell.value for cell in row))) for row in sheet.iter_rows(min_row=2)]


def keyed(rows, key="company_id"):
    return {clean(row.get(key)): row for row in rows if clean(row.get(key))}


def valid_date(value):
    try:
        parsed = dt.date.fromisoformat(clean(value)[:10])
        return parsed <= TODAY
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    workbook = openpyxl.load_workbook(args.workbook, read_only=True, data_only=True)
    companies = sheet_rows(workbook, "Companies DB")
    leadership = sheet_rows(workbook, "Leadership DB")
    market = sheet_rows(workbook, "Market Data")
    sources = sheet_rows(workbook, "Sources DB")
    funding = sheet_rows(workbook, "Funding Rounds") if "Funding Rounds" in workbook.sheetnames else []

    company_by_id = keyed(companies)
    leader_by_id = keyed(leadership)
    market_by_id = keyed(market)
    ids = set(company_by_id)
    source_ids = {clean(row.get("source_id")) for row in sources}
    funding_by_id = Counter(clean(row.get("company_id")) for row in funding)

    public_ids = {cid for cid, row in market_by_id.items() if clean(row.get("ownership_status")) == "Public"}
    private_ids = {cid for cid, row in market_by_id.items() if clean(row.get("ownership_status")) == "Private"}
    current_ids = {cid for cid, row in company_by_id.items() if clean(row.get("lifecycle_status")) == "Active"}

    def missing(predicate, dataset):
        return sorted(cid for cid, row in dataset.items() if not predicate(row))

    company_linkedin_missing = missing(lambda r: direct_linkedin_company(r.get("company_linkedin")), company_by_id)
    leadership_social_missing = missing(
        lambda r: direct_linkedin_person(r.get("linkedin_url"))
        or is_url(r.get("x_url")),
        leader_by_id,
    )
    leadership_photo_missing = missing(lambda r: is_url(r.get("photo_url")), leader_by_id)
    official_leader_source_missing = missing(lambda r: is_url(r.get("official_profile_url")), leader_by_id)

    future_funding = []
    weak_funding_rows = []
    for row in funding:
        cid = clean(row.get("company_id"))
        status = clean(row.get("event_status"))
        date = clean(row.get("announced_date"))
        if date and re.match(r"^20\d{2}-", date) and not valid_date(date):
            future_funding.append(clean(row.get("funding_event_id")))
        if status != "No public event located" and not is_url(row.get("source_url")):
            weak_funding_rows.append(clean(row.get("funding_event_id")))

    description_failures = []
    for cid, row in company_by_id.items():
        text = clean(row.get("description_short"))
        terminal = len(re.findall(r"[.!?](?:\s|$)", text))
        if len(text.split()) < 8 or terminal != 1:
            description_failures.append(cid)

    required_company_urls = {
        "official_website": missing(lambda r: is_url(r.get("official_website")), company_by_id),
        "logo_url": missing(lambda r: is_url(r.get("logo_url")), company_by_id),
    }
    public_missing = {
        "ticker": sorted(cid for cid in public_ids if not clean(market_by_id[cid].get("ticker"))),
        "yahoo_finance_url": sorted(cid for cid in public_ids if not is_url(market_by_id[cid].get("yahoo_finance_url"))),
        "investor_relations_url": sorted(cid for cid in public_ids if not is_url(market_by_id[cid].get("investor_relations_url"))),
    }
    private_missing = {
        "crunchbase_any": sorted(cid for cid in private_ids if not is_url(market_by_id[cid].get("crunchbase_url"))),
        "crunchbase_direct": sorted(cid for cid in private_ids if not direct_crunchbase(market_by_id[cid].get("crunchbase_url"))),
        "funding_resolution": sorted(cid for cid in private_ids if funding_by_id[cid] == 0),
        "unicorn_status": sorted(cid for cid in private_ids if not clean(market_by_id[cid].get("unicorn_status"))),
    }

    named_leader_missing = sorted(
        cid for cid in current_ids
        if clean(leader_by_id.get(cid, {}).get("full_name")).lower().startswith(
            ("not ", "no ", "research pending", "unknown")
        ) or not clean(leader_by_id.get(cid, {}).get("full_name"))
    )

    report = {
        "workbook": args.workbook,
        "audited_at": TODAY.isoformat(),
        "population": {
            "company_rows": len(companies),
            "unique_company_ids": len(ids),
            "leadership_rows": len(leadership),
            "market_rows": len(market),
            "public_companies": len(public_ids),
            "private_companies": len(private_ids),
        },
        "identity_integrity": {
            "company_leadership_ids_align": ids == set(leader_by_id),
            "company_market_ids_align": ids == set(market_by_id),
            "duplicate_company_ids": sorted(cid for cid, n in Counter(clean(r.get("company_id")) for r in companies).items() if n > 1),
            "missing_primary_source_ids": sorted(
                cid for cid, row in company_by_id.items()
                if clean(row.get("primary_source_id")) not in source_ids
            ),
        },
        "company_profile": {
            "official_website_verified": len(ids) - len(required_company_urls["official_website"]),
            "logo_url_verified": len(ids) - len(required_company_urls["logo_url"]),
            "linkedin_direct_verified": len(ids) - len(company_linkedin_missing),
            "meaningful_one_sentence_description": len(ids) - len(description_failures),
            "missing": {**required_company_urls, "company_linkedin": company_linkedin_missing, "description": description_failures},
        },
        "leadership": {
            "named_current_leader": len(current_ids) - len(named_leader_missing),
            "official_role_source_verified": len(ids) - len(official_leader_source_missing),
            "linkedin_person_verified": sum(direct_linkedin_person(r.get("linkedin_url")) for r in leadership),
            "verified_social_any": len(ids) - len(leadership_social_missing),
            "verified_photo": len(ids) - len(leadership_photo_missing),
            "research_status": Counter(clean(r.get("research_status")) for r in leadership),
            "missing": {
                "named_current_leader": named_leader_missing,
                "official_role_source": official_leader_source_missing,
                "verified_social_any": leadership_social_missing,
                "verified_photo": leadership_photo_missing,
            },
        },
        "market": {
            "public": {
                "population": len(public_ids),
                "yahoo_verified": len(public_ids) - len(public_missing["yahoo_finance_url"]),
                "missing": public_missing,
            },
            "private": {
                "population": len(private_ids),
                "crunchbase_any": len(private_ids) - len(private_missing["crunchbase_any"]),
                "crunchbase_direct": len(private_ids) - len(private_missing["crunchbase_direct"]),
                "funding_history_or_sourced_exception": len(private_ids) - len(private_missing["funding_resolution"]),
                "missing": private_missing,
            },
            "funding_rows": len(funding),
            "future_dated_events": future_funding,
            "event_rows_without_source_url": weak_funding_rows,
        },
    }
    output = json.dumps(report, indent=2, ensure_ascii=False, default=dict)
    if args.output:
        Path(args.output).write_text(output + "\n")
    print(output)


if __name__ == "__main__":
    main()
