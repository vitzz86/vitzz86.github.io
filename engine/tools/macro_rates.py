"""Source-aware macro-rate benchmarks for telemetry.

Yahoo's chart endpoint is reliable for traded tickers, but Indonesian policy
rates and SBN yields need dedicated sources. This module returns telemetry rows
with explicit units so the UI can show yield moves in basis points instead of
mislabeling them as equity-style returns.
"""
from __future__ import annotations

import datetime as dt
import html
import re
import time
import urllib.request

BI_RATE_URL = "https://www.bi.go.id/en/statistik/indikator/bi-rate.aspx"
ID10Y_URL = "https://www.investing.com/rates-bonds/indonesia-10-year-bond-yield"
UA = "Mozilla/5.0 (Project Cockpit; market telemetry)"


def _fetch(url: str) -> str | None:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:  # noqa: BLE001
            time.sleep(1.2 * (attempt + 1))
    return None


def _plain(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw or "")
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def _to_float(s: str | None) -> float | None:
    if s is None:
        return None
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:  # noqa: BLE001
        return None


def _ts(date_text: str) -> int | None:
    for fmt in ("%d %B %Y", "%b %d, %Y", "%d/%m/%Y"):
        try:
            d = dt.datetime.strptime(date_text.strip(), fmt)
            return int(dt.datetime(d.year, d.month, d.day, 12, tzinfo=dt.timezone.utc).timestamp())
        except ValueError:
            continue
    return None


def _rate_row(symbol: str, label: str, value: float, prev: float | None,
              url: str, source: str, spark: list[float] | None = None,
              spark_ts: list[int] | None = None, asof: str | None = None) -> dict:
    prev = value if prev is None else prev
    delta_bp = round((value - prev) * 100, 1)
    return {
        "symbol": symbol,
        "label": label,
        "kind": "rates" if symbol != "BI_RATE" else "policy",
        "value": round(value, 3),
        "value_unit": "percent",
        "delta_pct": delta_bp,
        "delta_unit": "bp",
        "prev_close": round(prev, 3),
        "state": "closed",
        "mkt_start": None,
        "mkt_end": None,
        "spark": spark or [],
        "spark_ts": spark_ts or [],
        "intraday": [prev, value] if prev != value else [],
        "url": url,
        "source_name": source,
        "asof": asof,
    }


def bi_rate() -> dict | None:
    raw = _fetch(BI_RATE_URL)
    if not raw:
        return None
    txt = _plain(raw)
    rows = []
    for date_text, val in re.findall(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+(\d+(?:\.\d+)?)\s*%", txt):
        v = _to_float(val)
        t = _ts(date_text)
        if v is not None:
            rows.append((date_text, t, v))
    if not rows:
        return None
    latest = rows[0]
    prev = rows[1][2] if len(rows) > 1 else latest[2]
    hist = list(reversed(rows[:12]))
    return _rate_row(
        "BI_RATE", "BI Rate", latest[2], prev, BI_RATE_URL, "Bank Indonesia",
        [v for _, _, v in hist], [t for _, t, _ in hist if t], latest[0],
    )


def indonesia_10y() -> dict | None:
    raw = _fetch(ID10Y_URL)
    if not raw:
        return None
    txt = _plain(raw)
    start = txt.lower().find("indonesia 10-year bond yield")
    snip = txt[start:start + 2600] if start >= 0 else txt[:2600]
    value = change = None
    patterns = [
        r"Currency in\s+IDR.*?([0-9]+(?:\.[0-9]+)?)\s+([+-][0-9]+(?:\.[0-9]+)?)\s*\(",
        r"Add to Watchlist\s+([0-9]+(?:\.[0-9]+)?)\s+([+-][0-9]+(?:\.[0-9]+)?)\s*\(",
        r"Prev\. Close\s+([0-9]+(?:\.[0-9]+)?).*?([0-9]+(?:\.[0-9]+)?)\s+([+-][0-9]+(?:\.[0-9]+)?)\s*\(",
    ]
    for pat in patterns:
        m = re.search(pat, snip, re.I)
        if m:
            nums = [_to_float(g) for g in m.groups()]
            nums = [n for n in nums if n is not None]
            if len(nums) >= 2:
                value, change = nums[-2], nums[-1]
                break
    if value is None:
        # Last fallback: the first yield-like number after the page title.
        nums = [_to_float(x) for x in re.findall(r"\b([4-9]\.\d{2,4})\b", snip)]
        nums = [n for n in nums if n is not None]
        if nums:
            value, change = nums[0], 0.0
    if value is None:
        return None
    prev = value - (change or 0.0)
    asof = None
    m_asof = re.search(r"Closed[·\s]+([0-9]{1,2}/[0-9]{1,2})", snip)
    if m_asof:
        asof = m_asof.group(1)
    return _rate_row(
        "ID10Y", "Indonesia 10Y SBN", value, prev, ID10Y_URL, "Investing.com",
        [prev, value] if prev != value else [], [], asof,
    )


def collect() -> dict[str, dict]:
    rows = {}
    for fn in (bi_rate, indonesia_10y):
        try:
            row = fn()
            if row:
                rows[row["symbol"]] = row
        except Exception as e:  # noqa: BLE001
            print(f"[macro_rates] {fn.__name__} failed: {e}")
    print(f"[macro_rates] {len(rows)} macro-rate benchmarks resolved")
    return rows
