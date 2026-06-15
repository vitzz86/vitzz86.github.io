"""Intellectual Diet — Podcast Agent (PRD v2).

Ingests RSS for a set of top-tier leadership / deep-thinking podcasts, takes the
newest episode of each, and distills a one-paragraph "Core Thesis" from the show
notes to optimize listening time. Uses a DeepSeek summarizer when a key is
configured; otherwise a clean extractive fallback. Every episode keeps its source
URL. When feeds are unreachable, a curated fallback set renders so the panel is
never empty.
"""
from __future__ import annotations

import re
import sys

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings


def _clean(html: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", html or "")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


_JUNK = re.compile(r"https?://|www\.|\b\d{1,2}:\d{2}\b|get your copy|subscribe|"
                   r"sponsor|patreon|follow us|available on|amazon|goodreads|"
                   r"timestamp|chapters?:|outline:|leave (a |your )?review|"
                   r"check out|sign up|promo code|discount|----|====", re.I)


def _extractive_thesis(raw: str, limit: int = 300) -> str:
    """Skip YouTube promo/links/timestamps; keep the first real prose sentences."""
    lines = [l.strip() for l in re.split(r"[\n\r]+", raw or "") if l.strip()]
    clean = [_clean(l) for l in lines if not _JUNK.search(l)]
    text = " ".join(clean).strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for p in parts:
        if len(p) < 25:
            continue
        if len(out) + len(p) > limit:
            break
        out += p + " "
    return out.strip()


FEED = "https://www.youtube.com/feeds/videos.xml?"


def collect(summarize=None, previous=None) -> list:
    """Two-category podcast diet (Brain · VC & Startup). Keeps episodes from the last
    PODCAST_WEEK_DAYS only, each tagged with its category and publish date.
    summarize: optional callable(system, user)->str for the DeepSeek Summary.
    previous: prior episodes — reuse a cached Summary (unchanged URL) and any resolved
    channel_ids so we don't re-summarize or re-resolve every run."""
    import datetime as _dt

    import feedparser

    from tools.videos import _resolve_channel_id

    now = _dt.datetime.now(_dt.timezone.utc)
    week_ago = now - _dt.timedelta(days=settings.PODCAST_WEEK_DAYS)
    prev = previous or []
    cache = {p["url"]: p["thesis"] for p in prev
             if p.get("url") and p.get("thesis")
             and not p["thesis"].startswith("New ")
             and not _JUNK.search(p["thesis"])          # don't reuse junky theses
             and len(p["thesis"]) > 40}
    id_cache = {p["channel_handle"].lstrip("@"): p["channel_id"]
                for p in prev if p.get("channel_handle") and p.get("channel_id")}

    eps = []
    for cat in settings.PODCAST_CATEGORIES:
        for show, kind, ref, host in cat["feeds"]:
            if kind == "playlist":
                url = FEED + "playlist_id=" + ref
            else:
                cid = _resolve_channel_id(ref, id_cache)
                url = (FEED + "channel_id=" + cid) if cid else None
            if not url:
                continue
            try:
                feed = feedparser.parse(url)
                kept = 0
                for e in feed.entries:
                    if kept >= settings.PODCAST_PER_SHOW:
                        break
                    title = (e.get("title") or "").strip()
                    link = (e.get("link") or "").strip()
                    pub = e.get("published_parsed")
                    if not title or not link or not pub:
                        continue
                    pub_dt = _dt.datetime(*pub[:6], tzinfo=_dt.timezone.utc)
                    if pub_dt < week_ago:          # ≤1 week only, drop the rest
                        continue
                    notes = e.get("summary") or e.get("description") or ""
                    if link in cache:
                        thesis = cache[link]
                    else:
                        thesis = ""
                        if summarize:
                            thesis = summarize(
                                "You are a sharp chief-of-staff briefing a busy investor on a "
                                "podcast episode they haven't heard. In 2-3 sentences (<=55 "
                                "words), state the single most important ARGUMENT or insight "
                                "and why it matters — not a description of topics. Be concrete. "
                                "No phrases like 'this episode discusses' or 'the guest talks about'.",
                                f"Podcast: {show} (host {host}). Episode title: {title}. "
                                f"Description: {_clean(notes)[:1400]}")
                        thesis = (thesis or "").strip() or _extractive_thesis(notes) \
                            or f"New {show} episode — open to listen."
                    eps.append({
                        "show": show, "host": host, "category": cat["key"],
                        "title": title[:140], "thesis": thesis[:340], "url": link,
                        "published": pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "ts": int(pub_dt.timestamp()),
                        "channel_handle": ref if kind == "channel" else "",
                        "channel_id": id_cache.get(ref.lstrip("@"), "") if kind == "channel" else "",
                    })
                    kept += 1
            except Exception as ex:  # noqa: BLE001
                print(f"[podcasts] {show} failed: {ex}")

    eps.sort(key=lambda p: p["ts"], reverse=True)     # newest first; client groups by category
    print(f"[podcasts] {len(eps)} episodes (≤{settings.PODCAST_WEEK_DAYS}d) "
          f"across {len(settings.PODCAST_CATEGORIES)} diets")
    if not eps:                          # total feed outage → curated fallback
        eps = [dict(fb, category="brain") for fb in settings.PODCAST_FALLBACK]
    return eps
