#!/usr/bin/env python3
"""Apply reviewed leadership/source corrections found in the final QA pass."""

from __future__ import annotations

import argparse
import datetime as dt

import openpyxl


TODAY = dt.date.today().isoformat()


CORRECTIONS = {
    "covariant": {
        "name": "Pieter Abbeel",
        "position": "Co-founder and Chief Scientist",
        "relationship": "Founder and current executive",
        "source": "https://covariant.ai/our-approach/",
    },
    "dci-indonesia": {
        "name": "Otto Toto Sugiri",
        "position": "Founder and President Director",
        "relationship": "Founder and current executive",
        "source": "https://dci-indonesia.com/corporate-governance/board-of-directors?content=2550f40e-2d72-46ef-847b-659a8e52add9",
    },
    "foxconn": {
        "name": "Young Liu",
        "position": "Chairman and CEO",
        "relationship": "Current executive",
        "source": "https://www.foxconn.com/en-us/investor-relations/corporate-governance/director?category=directors",
    },
    "github": {
        "name": "Jay Parikh",
        "position": "Executive Vice President, CoreAI, Microsoft",
        "relationship": "Parent-company executive listed by GitHub leadership",
        "source": "https://github.com/about/leadership",
        "linkedin": "https://www.linkedin.com/in/jayparikh/",
        "photo": "https://images.ctfassets.net/8aevphvgewt8/2Zbc3Hv83P7cmT3Il6mCOd/7cfc6eded0d93f88a30014c2806aad38/JayParikh.webp?fm=jpg&w=600",
        "photo_source": "https://github.com/about/leadership",
    },
    "meta": {
        "name": "Mark Zuckerberg",
        "position": "Founder, Chairman and Chief Executive Officer",
        "relationship": "Founder and current executive",
        "source": "https://investor.atmeta.com/leadership-and-governance/default.aspx",
    },
    "nabla": {
        "name": "Brian Manning",
        "position": "Chief Executive Officer",
        "relationship": "Current executive",
        "source": "https://www.nabla.com/about-us",
        "linkedin": "https://www.linkedin.com/in/briancmanning/",
        "photo": "https://cdn.prod.website-files.com/67c6ddc58c9e7b3f7d095cd9/6a58dd77a5100698c872bb94_Brian1.png",
        "photo_source": "https://www.nabla.com/about-us",
    },
    "qts": {
        "name": "Chad Williams",
        "position": "Chairman and Chief Executive Officer",
        "relationship": "Founder and current executive",
        "source": "https://qtsdatacenters.com/wp-content/uploads/2024/10/QTS-Sustainability-Report_2023_FINAL.pdf",
    },
    "scale-ai": {
        "name": "Francis deSouza",
        "position": "Chief Executive Officer",
        "relationship": "Current executive",
        "source": "https://scale.com/blog/scale-appoints-new-ceo",
        "linkedin": "https://www.linkedin.com/in/francisdesouza/",
        "photo": "https://cdn.sanity.io/images/50zba0eo/production/b2795d27120bf62150a2f3ceb667679a8b4ed018-3200x4800.jpg",
        "photo_source": "https://scale.com/blog/scale-appoints-new-ceo",
    },
    "smic": {
        "name": "Zhao Haijun",
        "position": "Co-Chief Executive Officer and Executive Director",
        "relationship": "Current executive",
        "source": "https://www.smics.com/uploads/e00981-2.pdf",
    },
    "vitro": {
        "name": "Victor S. Genuino",
        "position": "President and Chief Executive Officer, ePLDT and VITRO",
        "relationship": "Current executive",
        "source": "https://www.epldt.com/epldt-celebrates-25-years-eyes-launch-of-first-sovereign-ai-solutions-in-ph/",
    },
    "vllm": {
        "name": "Simon Mo",
        "position": "Project lead and core maintainer",
        "relationship": "Open-source project maintainer",
        "source": "https://docs.vllm.ai/en/stable/governance/committers/",
    },
    "ymtc": {
        "name": "Chen Nanxiang",
        "position": "Chairman and Acting CEO",
        "relationship": "Current executive",
        "source": "https://www.fpdchina.org/speaker/en/42",
    },
}


def clean(value):
    return " ".join(str(value or "").split())


def headers(ws):
    return {clean(cell.value): cell.column for cell in ws[1] if clean(cell.value)}


def rows_by_id(ws, index):
    return {clean(ws.cell(row, index["company_id"]).value): row for row in range(2, ws.max_row + 1)}


def setv(ws, index, row, field, value):
    if field in index:
        ws.cell(row, index[field], value)


def append_source(ws, company_id, company_name, source_url):
    index = headers(ws)
    source_id = f"SRC-IDENTITY-{company_id}-20260913"
    existing = {clean(ws.cell(row, index["source_id"]).value): row for row in range(2, ws.max_row + 1)}
    row = existing.get(source_id, ws.max_row + 1)
    values = {
        "source_id": source_id,
        "company_id": company_id,
        "company_name": company_name,
        "source_type": "Official leadership source",
        "publisher": "Official organisation",
        "source_title": f"Current leadership for {company_name}",
        "source_url": source_url,
        "publication_date": "See source",
        "accessed_at": TODAY,
        "reliability_tier": "Primary",
        "fields_supported": "Leadership name; position; current status; official portrait where provided",
        "notes": "Final identity QA correction; person/media identity checked together.",
    }
    for field, value in values.items():
        setv(ws, index, row, field, value)
    return source_id


def append_change(ws, company_id, previous, new, source_url):
    index = headers(ws)
    marker = f"CHG-IDENTITY-{company_id}-20260913"
    existing = {clean(ws.cell(row, index["change_id"]).value): row for row in range(2, ws.max_row + 1)}
    row = existing.get(marker, ws.max_row + 1)
    values = {
        "change_id": marker,
        "changed_at": TODAY,
        "company_id": company_id,
        "field_changed": "Leadership identity and evidence",
        "previous_value": previous,
        "new_value": new,
        "reason": "Final QA corrected stale/broken source URLs and removed mismatched leader portraits.",
        "source_url": source_url,
        "review_status": "Verified",
    }
    for field, value in values.items():
        setv(ws, index, row, field, value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    workbook = openpyxl.load_workbook(args.input)
    companies = workbook["Companies DB"]
    leaders = workbook["Leadership DB"]
    sources = workbook["Sources DB"]
    changes = workbook["Change Log"]
    ci, li = headers(companies), headers(leaders)
    cr, lr = rows_by_id(companies, ci), rows_by_id(leaders, li)
    updated = []
    for company_id, fact in CORRECTIONS.items():
        if company_id not in cr or company_id not in lr:
            continue
        c_row, l_row = cr[company_id], lr[company_id]
        company_name = clean(companies.cell(c_row, ci["display_name"]).value)
        old_name = clean(leaders.cell(l_row, li["full_name"]).value)
        old_photo = clean(leaders.cell(l_row, li["photo_url"]).value)
        source_id = append_source(sources, company_id, company_name, fact["source"])
        for field, value in {
            "full_name": fact["name"],
            "position": fact["position"],
            "relationship_type": fact["relationship"],
            "is_current": "Yes",
            "official_profile_url": fact["source"],
            "source_id": source_id,
            "last_verified_at": TODAY,
            "research_status": "Verified",
        }.items():
            setv(leaders, li, l_row, field, value)
        # A name change invalidates all inherited person-level media unless the
        # replacement value is explicitly reviewed in this correction set.
        if old_name.casefold() != fact["name"].casefold():
            for field in ("linkedin_url", "photo_url", "photo_source_url", "social_url", "social_platform", "social_source_url", "x_url", "x_handle", "x_source_url", "x_avatar_url", "x_last_verified_at", "x_verification_status"):
                setv(leaders, li, l_row, field, "")
        if fact.get("linkedin"):
            setv(leaders, li, l_row, "linkedin_url", fact["linkedin"])
            setv(leaders, li, l_row, "social_platform", "LinkedIn")
            setv(leaders, li, l_row, "social_url", fact["linkedin"])
            setv(leaders, li, l_row, "social_source_url", fact["source"])
            setv(leaders, li, l_row, "identity_check", "Matched name and organisation")
            setv(leaders, li, l_row, "social_verification_status", "Verified named-person LinkedIn URL")
        if fact.get("photo"):
            setv(leaders, li, l_row, "photo_url", fact["photo"])
            setv(leaders, li, l_row, "photo_source_url", fact.get("photo_source", fact["source"]))
            setv(leaders, li, l_row, "photo_verification_status", "Verified named-person portrait from official source")
        elif old_name.casefold() == fact["name"].casefold() and "photo" not in fact:
            # Preserve an already-reviewed same-person portrait.
            setv(leaders, li, l_row, "photo_url", old_photo)
        for field, value in {
            "current_leader_name": fact["name"],
            "current_leader_position": fact["position"],
            "last_verified_at": TODAY,
        }.items():
            setv(companies, ci, c_row, field, value)
        append_change(changes, company_id, old_name, fact["name"], fact["source"])
        updated.append(company_id)
    workbook.save(args.output)
    print(f"updated={len(updated)} ids={','.join(updated)} output={args.output}")


if __name__ == "__main__":
    main()
