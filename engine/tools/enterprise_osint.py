"""Agent 2 ingestion surface: enterprise OSINT feeds.

Standard route: parse the RSS matrix from settings cleanly via feedparser.
Anomaly route: add Tavily deep-search results scoped to the variance vector.
Jina Reader (r.jina.ai) is available as a markdown proxy for non-RSS targets.
"""
import sys

import requests

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))
from config import settings


def scan_feeds() -> dict:
    """Returns {category: [{"source","title","link"}...]} from the RSS matrix."""
    import feedparser

    headlines = {}
    for category, feeds in settings.RSS_FEEDS.items():
        bucket = []
        for source, url in feeds:
            try:
                parsed = feedparser.parse(url)
                for entry in parsed.entries[:4]:
                    title = (entry.get("title") or "").strip()
                    if title:
                        bucket.append({
                            "source": source,
                            "title": title[:220],
                            "link": entry.get("link", ""),
                        })
            except Exception as e:  # noqa: BLE001
                print(f"[osint] feed failed {source}: {e}")
        headlines[category] = bucket[: settings.MAX_HEADLINES_PER_CATEGORY]
    return headlines


def tavily_hunt(anomaly_desc: str) -> list:
    """Anomaly override: force web-search toward the specific variance vector."""
    if not settings.TAVILY_API_KEY:
        return []
    query = (f"Why did this happen today: {anomaly_desc}. Indonesia IDX JCI "
             f"regulatory macro cause, foreign institutional flows")
    try:
        r = requests.post(settings.TAVILY_ENDPOINT, json={
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "max_results": 5,
            "include_domains": ["reuters.com", "bloomberg.com", "ft.com",
                                "asia.nikkei.com", "businesstimes.com.sg"],
        }, timeout=30)
        r.raise_for_status()
        return [{"source": "Tavily", "title": it.get("title", "")[:220],
                 "link": it.get("url", "")} for it in r.json().get("results", [])]
    except Exception as e:  # noqa: BLE001
        print(f"[osint] tavily failed: {e}")
        return []


def jina_read(url: str, max_chars: int = 4000) -> str:
    """Fetch any page as clean markdown through the Jina Reader proxy."""
    try:
        r = requests.get(settings.JINA_READER_PREFIX + url, timeout=30)
        r.raise_for_status()
        return r.text[:max_chars]
    except Exception as e:  # noqa: BLE001
        print(f"[osint] jina read failed {url}: {e}")
        return ""
