"""Recent IPOs, upcoming offerings, and S&P 500 membership announcements.

The feature deliberately separates exchange IPOs from index membership changes:
companies list on IDX/Nasdaq/NYSE, while S&P 500 additions are announced by S&P
Dow Jones Indices. Data is cached in the baked payload so temporary upstream
blocks never erase the previous calendar.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request

from tools import news_router

NASDAQ_CALENDAR = "https://api.nasdaq.com/api/ipo/calendar"
NASDAQ_IPO_URL = "https://www.nasdaq.com/market-activity/ipos"
EIPO_URL = "https://www.e-ipo.co.id/id/ipo/index?view=list"
EIPO_READER = "https://r.jina.ai/https://www.e-ipo.co.id/id/ipo/index?view=list"
KSEI_URL = "https://web.ksei.co.id/publications/new-securities-registration?setLocale=id-ID"
SPDJI_URL = "https://www.spglobal.com/spdji/en/media-center/news-announcements/"
SEC_COMPANY_SEARCH = "https://www.sec.gov/edgar/browse/"
REFRESH_SECONDS = 6 * 3600
YEAR_SECONDS = 366 * 86400
SYNTHESIS_VIEWS = ("upcoming", "pipeline", "recent", "changes")


def _now() -> int:
    return int(dt.datetime.now(dt.timezone.utc).timestamp())


def _date_ts(value: str) -> int | None:
    value = (value or "").strip()
    for local, english in {
        "Januari": "January", "Februari": "February", "Maret": "March",
        "Mei": "May", "Juni": "June", "Juli": "July", "Agustus": "August",
        "Oktober": "October", "Desember": "December",
    }.items():
        value = re.sub(rf"\b{local}\b", english, value, flags=re.I)
    for fmt in ("%m/%d/%Y", "%d %b %Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return int(dt.datetime.strptime(value, fmt).replace(tzinfo=dt.timezone.utc).timestamp())
        except ValueError:
            pass
    return None


def _month_keys(now: dt.datetime, count: int = 13) -> list[str]:
    out = []
    year, month = now.year, now.month
    for _ in range(count):
        out.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    return out


def _future_month_keys(now: dt.datetime, count: int = 2) -> list[str]:
    out = []
    year, month = now.year, now.month
    for _ in range(count):
        month += 1
        if month == 13:
            year += 1
            month = 1
        out.append(f"{year:04d}-{month:02d}")
    return out


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nasdaq.com",
        "Referer": NASDAQ_IPO_URL,
    })
    with urllib.request.urlopen(req, timeout=18) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _nasdaq_month(month: str) -> dict:
    url = f"{NASDAQ_CALENDAR}?{urllib.parse.urlencode({'date': month})}"
    return _get_json(url).get("data") or {}


def _is_spac(name: str, ticker: str) -> bool:
    text = f"{name} {ticker}".lower()
    if "acquisition" in text or "blank check" in text or "merger corp" in text:
        return True
    # US IPO unit symbols conventionally end in U. Numbered shell names are a
    # second common SPAC form even when "acquisition" is omitted.
    if str(ticker or "").strip().upper().endswith("U"):
        return True
    return bool(re.search(
        r"\b(?:corp|corporation)\s+(?:II|III|IV|V|VI|VII|VIII|IX|X)\.?$"
        r"|\b(?:capital|equity partners|ventures)\s+(?:II|III|IV|V|VI|VII|VIII|IX|X),?\s+inc\.?$",
        str(name or "").strip(), re.I,
    ))


def _nasdaq_row(row: dict, status: str) -> dict | None:
    date_text = row.get("pricedDate") or row.get("expectedPriceDate") or row.get("filedDate")
    ts = _date_ts(date_text)
    ticker = str(row.get("proposedTickerSymbol") or "").strip().upper()
    name = str(row.get("companyName") or "").strip()
    if not name or not ts:
        return None
    return {
        "market": "US",
        "kind": "ipo",
        "status": status,
        "ticker": ticker,
        "name": name,
        "exchange": row.get("proposedExchange") or "US exchange",
        "event_ts": ts,
        "date_type": "filed_date" if status == "filed" else "listing_date",
        "price": row.get("proposedSharePrice"),
        "shares": row.get("sharesOffered"),
        "offer_amount": row.get("dollarValueOfSharesOffered"),
        "is_spac": _is_spac(name, ticker),
        "source": "Nasdaq IPO Calendar · EDGAR Online",
        "source_url": NASDAQ_IPO_URL,
        "official_filing_url": (
            f"{SEC_COMPANY_SEARCH}?CIK={urllib.parse.quote(ticker)}&owner=exclude&action=getcompany"
            if ticker else None
        ),
        "confidence": "official_calendar",
    }


def _enrich_us_classification(rows: list, snapshot: dict | None = None) -> dict:
    """Join Nasdaq IPO events to Nasdaq's actively traded security taxonomy."""
    if snapshot is None:
        try:
            from tools import index_membership
            snapshot = index_membership.us_market_snapshot()
        except Exception as exc:  # noqa: BLE001
            print(f"[ipo] Nasdaq industry enrichment failed: {exc}")
            snapshot = {}
    classified = 0
    for row in rows or []:
        ticker = str(row.get("ticker") or "").strip().upper().replace(".", "-").replace("/", "-")
        if ticker and not row.get("official_filing_url"):
            row["official_filing_url"] = (
                f"{SEC_COMPANY_SEARCH}?CIK={urllib.parse.quote(ticker)}&owner=exclude&action=getcompany"
            )
        market = (snapshot or {}).get(ticker) or {}
        industry = str(market.get("industry") or row.get("industry") or "").strip()
        sector = str(market.get("sector") or row.get("sector") or "").strip()
        if industry:
            row["industry"] = industry
            classified += 1
        if sector:
            row["sector"] = sector
        if industry.lower() == "blank checks":
            row["is_spac"] = True
    return {"rows": len(rows or []), "industry_classified": classified}


def _nasdaq(previous: dict) -> tuple[list, list, list, str]:
    previous_asof = int((previous or {}).get("us_asof") or 0)
    if previous_asof and "pipeline_us" in previous and _now() - previous_asof < REFRESH_SECONDS:
        return (list(previous.get("recent_us") or []),
                list(previous.get("upcoming_us") or []),
                list(previous.get("pipeline_us") or []), "cached")

    now_dt = dt.datetime.now(dt.timezone.utc)
    months = list(dict.fromkeys(_month_keys(now_dt, 13) + _future_month_keys(now_dt, 2)))
    payloads = {}
    try:
        with cf.ThreadPoolExecutor(max_workers=4) as pool:
            for month, data in zip(months, pool.map(_nasdaq_month, months)):
                payloads[month] = data
    except Exception as exc:  # noqa: BLE001
        print(f"[ipo] Nasdaq calendar failed: {exc}")
        return (list(previous.get("recent_us") or []),
                list(previous.get("upcoming_us") or []),
                list(previous.get("pipeline_us") or []), "stale_cache")

    recent, upcoming, pipeline, seen = [], [], [], set()
    cutoff = _now() - YEAR_SECONDS
    for data in payloads.values():
        priced = (((data.get("priced") or {}).get("rows")) or [])
        for raw in priced:
            row = _nasdaq_row(raw, "priced")
            key = (row or {}).get("ticker"), (row or {}).get("event_ts")
            if row and row["event_ts"] >= cutoff and key not in seen:
                seen.add(key)
                recent.append(row)
        upcoming_table = ((data.get("upcoming") or {}).get("upcomingTable") or {})
        for raw in upcoming_table.get("rows") or []:
            row = _nasdaq_row(raw, "expected")
            key = (row or {}).get("ticker"), (row or {}).get("event_ts")
            if row and row["event_ts"] >= _now() - 86400 and key not in seen:
                seen.add(key)
                upcoming.append(row)
        for raw in ((data.get("filed") or {}).get("rows") or []):
            row = _nasdaq_row(raw, "filed")
            key = (row or {}).get("ticker"), (row or {}).get("event_ts")
            if row and row["event_ts"] >= _now() - 120 * 86400 and key not in seen:
                seen.add(key)
                pipeline.append(row)
    recent.sort(key=lambda x: x["event_ts"], reverse=True)
    upcoming.sort(key=lambda x: x["event_ts"])
    pipeline.sort(key=lambda x: x["event_ts"], reverse=True)
    if not recent and previous.get("recent_us"):
        print("[ipo] Nasdaq calendar returned no recent rows; retaining previous calendar")
        return (list(previous.get("recent_us") or []),
                list(previous.get("upcoming_us") or []),
                list(previous.get("pipeline_us") or []), "stale_cache")
    return recent[:600], upcoming[:120], pipeline[:180], "live"


def _idx_recent(sectors: list) -> list:
    cutoff, seen, rows = _now() - YEAR_SECONDS, set(), []
    for sector in sectors or []:
        for asset in sector.get("constituents") or []:
            ts = int(asset.get("listing_ts") or 0)
            ticker = str(asset.get("ticker") or "").upper()
            if asset.get("country") != "ID" or ts < cutoff or ticker in seen:
                continue
            seen.add(ticker)
            rows.append({
                "market": "ID",
                "kind": "ipo",
                "status": "listed",
                "ticker": ticker,
                "name": asset.get("name") or ticker,
                "exchange": "IDX",
                "sector": sector.get("name"),
                "industry": asset.get("industry") or sector.get("name"),
                "event_ts": ts,
                "date_type": "listing_date",
                "price": None,
                "is_spac": False,
                "source": "TradingView first observed bar",
                "source_url": asset.get("source_url"),
                "confidence": "listing_date_proxy",
            })
    return sorted(rows, key=lambda x: x["event_ts"], reverse=True)


def _fetch_eipo_markdown() -> str:
    req = urllib.request.Request(EIPO_READER, headers={"User-Agent": "Project Cockpit"})
    with urllib.request.urlopen(req, timeout=20) as response:  # noqa: S310
        return response.read().decode("utf-8", "ignore")


def _eipo_upcoming(previous: dict) -> tuple[list, str]:
    try:
        text = _fetch_eipo_markdown()
    except Exception as exc:  # noqa: BLE001
        print(f"[ipo] e-IPO reader unavailable: {exc}")
        return list(previous.get("upcoming_id") or []), "stale_cache" if previous.get("upcoming_id") else "unavailable"
    if "under maintenance" in text.lower() or "site maintenance" in text.lower():
        return list(previous.get("upcoming_id") or []), "maintenance"

    out = _parse_eipo_markdown(text)
    if not out and previous.get("upcoming_id"):
        return list(previous.get("upcoming_id") or []), "stale_cache"
    return out, "live"


def _parse_eipo_markdown(text: str) -> list:
    """Parse both the current company-first and legacy status-first card layouts."""
    blocks = re.split(r"(?=###\s+[^\n]+\s*\([A-Z0-9]{3,6}\)\s*$)",
                      text, flags=re.I | re.M)
    if len(blocks) <= 1:
        blocks = re.split(
            r"(?=###\s+(?:Waiting For Offering|Offering|Book Building|Menunggu|Penawaran))",
            text, flags=re.I)
    out = []
    for block in blocks:
        company_match = re.search(
            r"###\s+([^\n]+?)\s*\(([A-Z0-9]{3,6})\)\s*$", block, re.I | re.M)
        if company_match:
            company, ticker = company_match.group(1).strip(), company_match.group(2).upper()
        else:
            legacy = re.search(r"#####\s+([^\n]+)\s*\n+\(([A-Z0-9]{3,6})\)", block, re.I)
            if not legacy:
                continue
            company, ticker = legacy.group(1).strip(), legacy.group(2).upper()
        status_match = re.search(
            r"^(Waiting For Offering|Offering|Book Building|Menunggu Penawaran|Penawaran|Closed)\s*$",
            block, re.I | re.M)
        status = status_match.group(1).strip().lower() if status_match else "scheduled"
        if status == "closed":
            continue
        date_match = re.search(
            r"(?:Tanggal Pencatatan|Expected Listing Date|Periode Penawaran|Periode Book Building)"
            r"[\s\S]{0,180}?((?:\d{1,2}\s+[A-Za-z]+\s+20\d{2})"
            r"(?:\s*-\s*\d{1,2}\s+[A-Za-z]+\s+20\d{2})?)", block, re.I)
        dates = re.findall(r"\d{1,2}\s+[A-Za-z]+\s+20\d{2}",
                           date_match.group(1) if date_match else block)
        ts = _date_ts(dates[-1]) if dates else None
        price_match = re.search(
            r"(?:Harga Final|Harga Penawaran|Rentang Harga Book Building)[\s\S]{0,100}?"
            r"(?:Rp|IDR)\s*([\d.,]+(?:\s*-\s*(?:Rp|IDR)?\s*[\d.,]+)?)", block, re.I)
        sector_match = re.search(r"(?:#####\s*)?Sektor\s*\n+([^\n#]+)", block, re.I)
        shares_match = re.search(r"(?:#####\s*)?Saham Ditawarkan\s*\n+([^\n#]+)", block, re.I)
        prospectus_match = re.search(
            r"\[[^\]]*Prospektus[^\]]*\]\((https?://[^)]+)\)", block, re.I)
        if not prospectus_match:
            prospectus_match = re.search(
                r"(https?://[^\s)]+/pipeline/get-propectus-file\?[^\s)]+)", block, re.I)
        detail_match = re.search(
            r"\[[^\]]*(?:Info lebih lanjut|Informasi Lainnya)[^\]]*\]\((https?://[^)]+)\)",
            block, re.I)
        out.append({
            "market": "ID", "kind": "ipo", "status": status,
            "ticker": ticker, "name": company or ticker, "exchange": "IDX",
            "event_ts": ts, "date_type": "listing_or_offering_date",
            "price": price_match.group(1).strip() if price_match else None,
            "sector": sector_match.group(1).strip() if sector_match else None,
            "shares": shares_match.group(1).strip() if shares_match else None,
            "prospectus_url": prospectus_match.group(1).strip() if prospectus_match else None,
            "detail_url": detail_match.group(1).strip() if detail_match else None,
            "is_spac": False,
            "source": "e-IPO Indonesia", "source_url": EIPO_URL,
            "confidence": "official_calendar",
        })
    out = [row for row in out if row.get("event_ts") is None or row["event_ts"] >= _now() - 86400]
    return sorted(out, key=lambda x: x.get("event_ts") or 10**12)


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Project Cockpit"})
    with urllib.request.urlopen(req, timeout=22) as response:  # noqa: S310
        return response.read().decode("utf-8", "ignore")


def _parse_ksei_html(text: str) -> list:
    """Extract official equity IPO registration notices and their PDF links."""
    rows = []
    for block in re.findall(r"<article\b[\s\S]*?</article>", text, re.I):
        title_match = re.search(
            r"<p[^>]*>\s*Penawaran Umum Perdana atas Saham\s+([\s\S]*?)</p>", block, re.I)
        if not title_match:
            continue
        company = re.sub(r"<[^>]+>", " ", title_match.group(1))
        company = re.sub(r"\s+", " ", html.unescape(company)).strip()
        date_match = re.search(r"<small[^>]*>[\s\S]*?<b>([^<]+)</b>", block, re.I)
        href_match = re.search(r'href="([^"]+\.pdf)"', block, re.I)
        ts = _date_ts(html.unescape(date_match.group(1)).strip()) if date_match else None
        if not company or not ts or not href_match:
            continue
        href = urllib.parse.urljoin(KSEI_URL, html.unescape(href_match.group(1)))
        rows.append({
            "market": "ID", "kind": "ipo_registration", "status": "registered",
            "ticker": "", "name": company, "exchange": "IDX", "event_ts": ts,
            "date_type": "registration_date", "is_spac": False,
            "source": "KSEI official registration", "source_url": href,
            "official_filing_url": href, "confidence": "official_registration",
        })
    return sorted(rows, key=lambda row: row["event_ts"], reverse=True)


def _name_key(value: str) -> str:
    value = re.sub(r"\b(?:pt|tbk|perseroan|the|inc|corp|ltd)\b", " ", value or "", flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _ksei_pipeline(recent_id: list, previous: dict) -> tuple[list, str]:
    try:
        filings = _parse_ksei_html(_fetch_text(KSEI_URL))
    except Exception as exc:  # noqa: BLE001
        print(f"[ipo] KSEI registrations failed: {exc}")
        cached = list(previous.get("pipeline_id_official") or [])
        return cached, "stale_cache" if cached else "unavailable"
    recent_names = [(_name_key(row.get("name")), row) for row in recent_id]
    unmatched = []
    for filing in filings:
        key = _name_key(filing.get("name"))
        match = next((row for name, row in recent_names
                      if key and name and (key in name or name in key)), None)
        if match:
            match["official_filing_url"] = filing["official_filing_url"]
            match["official_filing_source"] = filing["source"]
        elif filing["event_ts"] >= _now() - 60 * 86400:
            unmatched.append(filing)
    return unmatched[:30], "live"


def _reported_id_pipeline(previous: dict, wire: list, recent_id: list) -> tuple[list, str]:
    previous_asof = int(previous.get("id_pipeline_asof") or 0)
    if previous_asof and _now() - previous_asof < REFRESH_SECONDS:
        return list(previous.get("pipeline_id_reported") or []), "cached"
    items = list(wire or [])
    for query in ("rencana IPO Indonesia BEI perusahaan 2026",
                  "akan IPO bursa Indonesia emiten 2026",
                  "pipeline IPO Indonesia BEI"):
        items += news_router.google_news(
            query, "ID", 10, category="MARKETS_FINANCE", query_type="ipo", days=90)
    allowed = ("cnbc indonesia", "bloomberg technoz", "kontan", "bisnis", "investor.id",
               "emitennews", "idx channel", "kabar bursa", "idnfinancials", "antara",
               "stockbit", "ajaib", "detikfinance", "kompas")
    out, seen = [], set()
    recent_tickers = {str(row.get("ticker") or "").lower() for row in recent_id if row.get("ticker")}
    latest_listing = max((int(row.get("event_ts") or 0) for row in recent_id), default=0)
    report_cutoff = max(_now() - 30 * 86400, latest_listing)
    for item in sorted(items, key=lambda x: int(x.get("ts") or 0), reverse=True):
        title = str(item.get("title") or "").strip()
        source = str(item.get("source") or "").strip()
        low = title.lower()
        if "ipo" not in low or not any(term in low for term in
                ("rencana", "akan", "siap", "pipeline", "antre", "calon emiten")):
            continue
        if int(item.get("ts") or 0) < report_cutoff:
            continue
        if any(re.search(rf"\b{re.escape(ticker)}\b", low) for ticker in recent_tickers):
            continue
        if not any(term in source.lower() for term in allowed):
            continue
        key = re.sub(r"[^a-z0-9]+", " ", low).strip()
        if not item.get("url") or key in seen:
            continue
        seen.add(key)
        out.append({
            "market": "ID", "kind": "pipeline_report", "status": "reported pipeline",
            "ticker": "", "name": title, "exchange": "IDX candidate",
            "event_ts": int(item.get("ts") or 0), "date_type": "publication_date",
            "is_spac": False, "source": source, "source_url": item["url"],
            "confidence": "reported_not_scheduled", "related_news": [item],
        })
    if not out:
        cached = list(previous.get("pipeline_id_reported") or [])
        return cached, "stale_cache" if cached else "unavailable"
    return out[:10], "live"


def _attach_related(rows: list, wire: list) -> None:
    for row in rows:
        if row.get("related_news"):
            continue
        ticker = str(row.get("ticker") or "").lower()
        words = [w for w in re.findall(r"[a-z0-9]+", str(row.get("name") or "").lower())
                 if len(w) >= 5 and w not in {"indonesia", "company", "perseroan"}]
        matches = []
        for item in wire or []:
            text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
            if ticker and re.search(rf"\b{re.escape(ticker)}\b", text):
                matches.append(item)
            elif words and sum(word in text for word in words[:5]) >= 2:
                matches.append(item)
        row["related_news"] = matches[:3]


def _human_list(items: list[str]) -> str:
    clean = [str(item).strip() for item in items if str(item or "").strip()]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    return ", ".join(clean[:-1]) + f", and {clean[-1]}"


def _ipo_view_rows(payload: dict, view: str, market: str) -> list:
    keys = {
        "upcoming": ("upcoming_id", "upcoming_us"),
        "pipeline": ("pipeline_id", "pipeline_us"),
        "recent": ("recent_id", "recent_us"),
        "changes": (None, "sp500_changes"),
    }[view]
    key = keys[0] if market == "ID" else keys[1]
    return list(payload.get(key) or []) if key else []


def _ipo_fact_line(payload: dict, view: str, market: str) -> str:
    rows = [row for row in _ipo_view_rows(payload, view, market) if not row.get("is_spac")]
    label = "Indonesia" if market == "ID" else "US/global"
    if not rows:
        if view == "changes" and market == "ID":
            return "Indonesia: S&P 500 membership changes apply to the US benchmark and have no Indonesian listing event in this view."
        return f"{label}: no verified {view} IPO event currently passes the source and quality checks."
    industries: dict[str, int] = {}
    for row in rows:
        industry = str(row.get("industry") or row.get("sector") or "").strip()
        if industry and industry.lower() != "industry unavailable":
            industries[industry] = industries.get(industry, 0) + 1
    top_industries = [name for name, _count in sorted(
        industries.items(), key=lambda item: (-item[1], item[0]))[:3]]
    names = [str(row.get("ticker") or row.get("name") or "").strip() for row in rows[:3]]
    focus = f", led by {_human_list(names)}" if names else ""
    mix = f"; the most represented industries are {_human_list(top_industries)}" if top_industries else ""
    singular, plural = {
        "upcoming": ("verified scheduled listing", "verified scheduled listings"),
        "pipeline": ("filed or reported pipeline candidate", "filed or reported pipeline candidates"),
        "recent": ("listing in the past year", "listings in the past year"),
        "changes": ("S&P 500 membership announcement", "S&P 500 membership announcements"),
    }[view]
    wording = singular if len(rows) == 1 else plural
    return f"{label}: {len(rows)} {wording} are currently tracked{focus}{mix}."


def _deterministic_synthesis(payload: dict) -> dict:
    return {
        view: {
            "indonesia": _ipo_fact_line(payload, view, "ID"),
            "us": _ipo_fact_line(payload, view, "US"),
        }
        for view in SYNTHESIS_VIEWS
    }


def _synthesis_signature(payload: dict) -> str:
    compact = {}
    for view in SYNTHESIS_VIEWS:
        for market in ("ID", "US"):
            compact[f"{view}_{market}"] = [
                [row.get("ticker"), row.get("name"), row.get("status"), row.get("event_ts"),
                 row.get("industry") or row.get("sector")]
                for row in _ipo_view_rows(payload, view, market) if not row.get("is_spac")
            ]
    raw = json.dumps(compact, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _parse_synthesis(raw: str) -> dict | None:
    if not raw:
        return None
    try:
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(raw).strip(), flags=re.I)
        obj = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None
    for view in SYNTHESIS_VIEWS:
        block = obj.get(view)
        if not isinstance(block, dict):
            return None
        for region in ("indonesia", "us"):
            if not isinstance(block.get(region), str) or not block[region].strip():
                return None
            block[region] = block[region].strip()[:420]
    return obj


def _compile_synthesis(payload: dict, previous: dict, summarize=None) -> tuple[dict, str]:
    signature = _synthesis_signature(payload)
    cached = previous.get("synthesis") if previous.get("synthesis_signature") == signature else None
    if isinstance(cached, dict) and all(isinstance(cached.get(view), dict) for view in SYNTHESIS_VIEWS):
        return cached, signature
    fallback = _deterministic_synthesis(payload)
    if not summarize:
        return fallback, signature
    facts = "\n".join(
        f"{view.upper()} | {fallback[view]['indonesia']} | {fallback[view]['us']}"
        for view in SYNTHESIS_VIEWS
    )
    raw = summarize(
        "You summarize an IPO radar for an Indonesia-focused investor. Return raw JSON only with keys "
        "upcoming, pipeline, recent, and changes; each key must contain indonesia and us. Write exactly "
        "one concise, complete sentence per region. Use only the supplied facts, preserve all counts and "
        "company/ticker names, distinguish confirmed schedules from filed/reported pipeline, and never invent "
        "dates, demand, valuation, offer size, or market implications. If no verified event exists, say so plainly.",
        facts,
    )
    return _parse_synthesis(raw) or fallback, signature


def _sp500_changes() -> list:
    items = news_router.google_news(
        '"S&P 500" constituent changes addition', "US", 20,
        category="MARKETS_FINANCE", site="spglobal.com", query_type="official", days=365)
    relevant = []
    for item in items:
        title = str(item.get("title") or "").lower()
        if "s&p 500" in title and any(term in title for term in ("change", "add", "join", "replace", "constituent")):
            relevant.append(item)
    return [{
        "market": "SP500", "kind": "index_change", "status": "announced",
        "ticker": "", "name": item.get("title"), "exchange": "S&P 500",
        "event_ts": item.get("ts"), "source": item.get("source") or "S&P Dow Jones Indices",
        "source_url": item.get("url") or SPDJI_URL, "confidence": "official_announcement",
    } for item in relevant if item.get("url")][:20]


def collect(sectors: list, previous: dict | None = None, news_wire: list | None = None,
            summarize=None) -> dict:
    previous = previous or {}
    news_wire = news_wire or []
    recent_us, upcoming_us, pipeline_us, us_health = _nasdaq(previous)
    us_classification = _enrich_us_classification(recent_us + upcoming_us + pipeline_us)
    upcoming_id, id_health = _eipo_upcoming(previous)
    recent_id = _idx_recent(sectors)
    if not recent_id and previous.get("recent_id"):
        print("[ipo] IDX listing timestamps absent in this payload; retaining previous Recent 1Y rows")
        recent_id = list(previous.get("recent_id") or [])
    pipeline_id_official, ksei_health = _ksei_pipeline(recent_id, previous)
    pipeline_id_reported, report_health = _reported_id_pipeline(previous, news_wire, recent_id)
    pipeline_id = pipeline_id_official + pipeline_id_reported
    for rows in (recent_id, recent_us, upcoming_id, upcoming_us, pipeline_id, pipeline_us):
        _attach_related(rows, news_wire)
    sp500 = _sp500_changes()
    now = _now()
    payload = {
        "as_of": now,
        "us_asof": now if us_health == "live" else int(previous.get("us_asof") or 0),
        "recent_id": recent_id,
        "recent_us": recent_us,
        "upcoming_id": upcoming_id,
        "upcoming_us": upcoming_us,
        "pipeline_id": pipeline_id,
        "pipeline_us": pipeline_us,
        "pipeline_id_official": pipeline_id_official,
        "pipeline_id_reported": pipeline_id_reported,
        "id_pipeline_asof": now if report_health == "live" else int(previous.get("id_pipeline_asof") or 0),
        "sp500_changes": sp500 or list(previous.get("sp500_changes") or []),
        "health": {
            "idx_recent": "tradingview_listing_proxy",
            "idx_upcoming": id_health,
            "idx_registration": ksei_health,
            "idx_pipeline_reports": report_health,
            "us_calendar": us_health,
            "us_industry": us_classification,
            "sp500": "live" if sp500 else "stale_cache" if previous.get("sp500_changes") else "unavailable",
        },
        "recent_window_days": 365,
        "note": "S&P 500 entries are index membership announcements, not IPOs.",
    }
    payload["synthesis"], payload["synthesis_signature"] = _compile_synthesis(
        payload, previous, summarize=summarize)
    print(f"[ipo] recent={len(recent_id)} ID/{len(recent_us)} US · "
          f"scheduled={len(upcoming_id)} ID/{len(upcoming_us)} US · "
          f"pipeline={len(pipeline_id)} ID/{len(pipeline_us)} US · S&P changes={len(payload['sp500_changes'])}")
    return payload
