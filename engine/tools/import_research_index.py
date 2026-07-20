"""Convert the maintained research-index workbook into Cockpit JSON.

The importer intentionally uses only the Python standard library so it can run
in a clean checkout without adding an Excel dependency to the market pipeline.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _column(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref or "A").group(0)
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - 64
    return value - 1


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(node.text or "" for node in item.findall(".//m:t", NS))
            for item in root.findall("m:si", NS)]


def _sheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("r:Relationship", REL_NS)}
    for sheet in workbook.findall(".//m:sheet", NS):
        if sheet.attrib.get("name") == sheet_name:
            rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = targets[rel_id].lstrip("/")
            return target if target.startswith("xl/") else "xl/" + target
    raise ValueError(f"Workbook has no sheet named {sheet_name!r}")


def read_sheet(path: Path, sheet_name: str = "Master Index") -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        strings = _shared_strings(archive)
        root = ET.fromstring(archive.read(_sheet_path(archive, sheet_name)))
        rows = []
        for row in root.findall(".//m:sheetData/m:row", NS):
            values: dict[int, str] = {}
            for cell in row.findall("m:c", NS):
                value = cell.find("m:v", NS)
                inline = cell.find("m:is", NS)
                raw = value.text if value is not None else "".join(
                    node.text or "" for node in (inline.findall(".//m:t", NS) if inline is not None else []))
                if cell.attrib.get("t") == "s" and raw:
                    raw = strings[int(raw)]
                values[_column(cell.attrib.get("r", "A1"))] = str(raw or "").strip()
            if values:
                rows.append([values.get(i, "") for i in range(max(values) + 1)])
    if not rows:
        return []
    headers = [str(value).strip() for value in rows[0]]
    return [{headers[i]: value for i, value in enumerate(row) if i < len(headers) and headers[i]}
            for row in rows[1:] if any(str(value).strip() for value in row)]


def normalize(rows: list[dict]) -> dict:
    key_map = {
        "Priority Tier": "priority", "Category": "category", "Subcategory": "subcategory",
        "Geography": "geography", "Report Title": "title", "Publisher": "publisher",
        "Published": "published", "Coverage / Edition": "coverage", "Format": "format",
        "Access": "access", "Direct PDF / Download URL": "direct_url",
        "Official Landing Page": "landing_url", "H1 2026 Relevance": "relevance",
        "Why It Is Useful": "why_useful", "Verification": "verification", "Verified On": "verified_on",
    }
    reports = []
    for index, row in enumerate(rows, 1):
        item = {target: str(row.get(source) or "").strip() for source, target in key_map.items()}
        if not item["title"] or not (item["direct_url"] or item["landing_url"]):
            continue
        item["id"] = f"curated-{index:03d}"
        item["source_type"] = "curated_index"
        item["source_url"] = item["direct_url"] or item["landing_url"]
        item["ticker_tags"] = []
        item["sector_tags"] = []
        reports.append(item)
    return {
        "schema_version": 1,
        "source": "H1_2026_Investment_Market_Report_Index.xlsx",
        "report_count": len(reports),
        "reports": reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Project Cockpit research workbook")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = normalize(read_sheet(args.workbook))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {payload['report_count']} research reports into {args.output}")


if __name__ == "__main__":
    main()
