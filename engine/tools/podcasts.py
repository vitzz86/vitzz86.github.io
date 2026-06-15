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
                   r"timestamp|chapters?:|outline:", re.I)


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


def collect(summarize=None) -> list:
    """summarize: optional callable(system, user)->str for DeepSeek Core Thesis."""
    import feedparser

    eps = []
    for show, url, host in settings.PODCAST_FEEDS:
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                continue
            e = feed.entries[0]
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            notes = e.get("summary") or e.get("description") or ""
            if not title or not link:
                continue
            thesis = ""
            if summarize:
                thesis = summarize(
                    "You are a sharp chief-of-staff briefing a busy investor on a podcast "
                    "episode they haven't heard. In 2-3 sentences (<=55 words), state the "
                    "single most important ARGUMENT or insight of the episode and why it "
                    "matters — not a description of topics. Be concrete and specific. No "
                    "phrases like 'this episode discusses' or 'the guest talks about'.",
                    f"Podcast: {show} (host {host}). Episode title: {title}. "
                    f"Description: {_clean(notes)[:1400]}")
            thesis = (thesis or "").strip() or _extractive_thesis(notes) \
                or f"New {show} episode — open to listen."
            eps.append({"show": show, "host": host, "title": title[:140],
                        "thesis": thesis[:340], "url": link})
        except Exception as ex:  # noqa: BLE001
            print(f"[podcasts] {show} failed: {ex}")

    if len(eps) < 4:                       # thin feeds → top up with curated set
        seen = {e["show"] for e in eps}
        for fb in settings.PODCAST_FALLBACK:
            if fb["show"] not in seen:
                eps.append(dict(fb))
    print(f"[podcasts] {len(eps)} episodes distilled")
    return eps[:5]
