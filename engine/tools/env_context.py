"""Environmental baseline tools: clock, weather, calendar load, verse, soundtrack.

Everything here degrades gracefully — a failed fetch never raises past the
public helpers, so the orchestrator can always assemble the `opening` block.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import urllib.request

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings


def now_wib() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=settings.WIB_UTC_OFFSET)


def greeting(hour: int | None = None) -> str:
    h = now_wib().hour if hour is None else hour
    if 4 <= h < 11:
        return "Good morning, Vito. Let's process the boards."
    if 11 <= h < 15:
        return "Good afternoon, Vito. Midday telemetry is in."
    if 15 <= h < 19:
        return "Good evening, Vito. Closing signals are settling."
    return "Late session, Vito. The desks are quiet — here's the wrap."


# ------------------------------------------------------------------ weather
_WMO = {  # Open-Meteo weather codes -> short description
    0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    80: "Patchy rain", 81: "Rain showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Severe thunderstorm",
}


def _fetch_json(url: str, timeout: int = 15):
    import json
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def weather() -> dict:
    """Returns {"bsd": str, "jakarta": str, "insight": str, "_rainy": bool}."""
    out, rainy, hot = {}, False, False
    for key, loc in settings.LOCATIONS.items():
        try:
            url = (f"{settings.OPEN_METEO}?latitude={loc['lat']}&longitude={loc['lon']}"
                   f"&current=temperature_2m,weather_code&timezone=Asia%2FJakarta")
            cur = _fetch_json(url)["current"]
            code, temp = int(cur["weather_code"]), round(cur["temperature_2m"])
            desc = _WMO.get(code, "Mixed conditions")
            out[key] = f"{desc}, {temp}°C."
            rainy = rainy or code >= 51
            hot = hot or temp >= 32
        except Exception as e:  # noqa: BLE001 — keep the brief alive
            print(f"[env_context] weather fetch failed for {key}: {e}")
            out[key] = "Telemetry unavailable."
    if rainy:
        out["insight"] = ("High precipitation across the corridor. Pad commute windows "
                          "and maximize internal focus blocks.")
    elif hot:
        out["insight"] = ("High thermal load midday. Schedule outdoor movement early; "
                          "hydrate before afternoon syncs.")
    else:
        out["insight"] = ("Clear operating window. Good day to front-load external "
                          "meetings and site movement.")
    out["_rainy"] = rainy
    return out


# ------------------------------------------------------------------ calendar
def focus_state() -> str:
    """Cognitive bandwidth pill from the secret Google Calendar ICS feed."""
    if not settings.GCAL_ICS_URL:
        return "Deep Work Priority (Low Sync Load)"
    try:
        with urllib.request.urlopen(settings.GCAL_ICS_URL, timeout=20) as r:
            ics = r.read().decode("utf-8", "ignore")
        today = now_wib().strftime("%Y%m%d")
        hours = 0.0
        for ev in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics, re.S):
            m = re.search(r"DTSTART[^:]*:(\d{8})T(\d{4})", ev)
            n = re.search(r"DTEND[^:]*:(\d{8})T(\d{4})", ev)
            if m and n and m.group(1) == today:
                start = int(m.group(2)[:2]) * 60 + int(m.group(2)[2:])
                end = int(n.group(2)[:2]) * 60 + int(n.group(2)[2:])
                hours += max(0, end - start) / 60
        if hours >= 4:
            return "\U0001F465 High Sync Maintenance (Heavy Meeting Load)"
        if hours >= 2:
            return "Balanced Cadence (Moderate Sync Load)"
        return "⚡ Deep Work Focus (Low Sync Load)"
    except Exception as e:  # noqa: BLE001
        print(f"[env_context] calendar fetch failed: {e}")
        return "Deep Work Priority (Low Sync Load)"


# ------------------------------------------------------------------ verse + sound
def verse_of_the_day() -> str:
    """Live daily scripture from bible-api.com (keyless); falls back to the
    curated pool when offline. A themed verse list seeds the random query so the
    rotation stays grounded rather than fully arbitrary."""
    seeds = ["proverbs+16:3", "philippians+4:13", "isaiah+40:29", "jeremiah+29:11",
             "psalm+118:24", "colossians+3:23", "proverbs+3:5-6", "matthew+6:33",
             "1+corinthians+16:14", "deuteronomy+31:6", "philippians+4:6",
             "proverbs+21:5", "joshua+1:9", "romans+8:28"]
    _n = now_wib()
    bucket = _n.timetuple().tm_yday * 8 + _n.hour // 3   # rotate every 3h (aligns with Daily Brief)
    ref = seeds[bucket % len(seeds)]
    try:
        data = _fetch_json(f"https://bible-api.com/{ref}", timeout=12)
        text = (data.get("text") or "").strip().replace("\n", " ")
        ref_disp = data.get("reference", "")
        if text and ref_disp:
            return f"{text} — {ref_disp}"
    except Exception as e:  # noqa: BLE001
        print(f"[env_context] verse fetch failed: {e}")
    return settings.VERSES[bucket % len(settings.VERSES)]


# ------------------------------------------------------------------ note webhook
def note_of_the_day(previous: str | None = None) -> str:
    if settings.NOTE_URL:
        try:
            with urllib.request.urlopen(settings.NOTE_URL, timeout=20) as r:
                txt = r.read().decode("utf-8", "ignore").strip()
            txt = re.sub(r"<[^>]+>", "", txt)          # sanitize layout elements
            txt = re.sub(r"\s+", " ", txt).strip()
            if txt:
                return txt[:600]
        except Exception as e:  # noqa: BLE001
            print(f"[env_context] note fetch failed: {e}")
    return previous or settings.FALLBACK_NOTE
