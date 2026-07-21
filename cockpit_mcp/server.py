"""MCP transport for the Project Cockpit read-only intelligence service."""

from __future__ import annotations

import argparse
import os
from typing import List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

from .service import CockpitService


INSTRUCTIONS = """
Project Cockpit is the first source for covered market, ticker, chart, score,
news, video, IPO, macro, and research questions. Do not inspect or scrape the
dashboard UI for data exposed by a Cockpit tool. For ticker analysis call
get_company_evidence, then get_asset_chart and get_asset_score. For cross-firm
or period research call build_research_synthesis before any generic workflow or
web search. Treat the score as a deterministic screening opinion, not an
investment recommendation: report opportunity score, data-confidence percent,
factor weaknesses, valuation confidence, and limitations. Reconcile contrary
source-linked research; never force evidence to match Cockpit or another AI.
External browsing is gap-fill only: open indexed source_url records
or find publishers explicitly reported missing. Always state payload time,
market state, provider, score mode, confidence, chart quality, and warnings.
Research metadata is discovery evidence, not report content. Exact technical
levels, candlestick patterns, and volume confirmation require explicit OHLCV
data. Never invent missing fundamentals, targets, transcripts, causal claims,
transaction data, or recommendations.
""".strip()

service = CockpitService()
READ_ONLY_TOOL = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


def _csv_env(name: str) -> List[str]:
    return [value.strip() for value in os.getenv(name, "").split(",") if value.strip()]


allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"] + _csv_env("COCKPIT_MCP_ALLOWED_HOSTS")
allowed_origins = [
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
] + _csv_env("COCKPIT_MCP_ALLOWED_ORIGINS")
mcp = FastMCP(
    "Project Cockpit",
    instructions=INSTRUCTIONS,
    json_response=True,
    stateless_http=True,
    host=os.getenv("COCKPIT_MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("COCKPIT_MCP_PORT", "8790")),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    ),
)


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health_check(_: Request) -> JSONResponse:
    """Lightweight health endpoint for container platforms."""
    try:
        status = service.status()
        return JSONResponse({
            "status": "ok",
            "service": status.get("service"),
            "payload_timestamp": status.get("payload_timestamp"),
            "contract_health": status.get("contract_health"),
        })
    except RuntimeError as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=503)


@mcp.tool(annotations=READ_ONLY_TOOL)
def cockpit_status() -> dict:
    """Check payload freshness, coverage counts, and provider health."""
    return service.status()


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_market_telemetry(symbol: str = "", include_chart: bool = False) -> dict:
    """Get indices, commodities, FX, crypto, and macro-rate telemetry; optionally include chart points."""
    return service.market_telemetry(symbol, include_chart)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_macro_indicators(view: str = "core", pillar: str = "") -> dict:
    """Get source-linked Indonesia macro releases; view is core, detail, ratings, or country_risk."""
    return service.macro_indicators(view, pillar)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_market_heatmap(market: str = "id", sector: str = "", limit: int = 120) -> dict:
    """Get market-cap-sized, return-colored heatmap assets grouped by sector for ID, S&P 500, Nasdaq 100, US, crypto, or others."""
    return service.heatmap(market, sector, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_trending_assets(market: str = "all", mode: str = "all") -> dict:
    """Get baked gainers, losers, top-score, active, and social-trending signals."""
    return service.trending(market, mode)


@mcp.tool(annotations=READ_ONLY_TOOL)
def search_assets(query: str = "", market: str = "all", sector: str = "", limit: int = 15) -> dict:
    """Search Cockpit's full asset universe by ticker, name, industry, sector, or country."""
    return service.search_assets(query, market, sector, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_asset(ticker: str, country: str = "") -> dict:
    """Get quote, market state, performance, liquidity, technicals, source, and score summary for one asset."""
    return service.get_asset(ticker, country)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_asset_chart(ticker: str, timeframe: str = "1M", country: str = "") -> dict:
    """Primary chart tool: get points, deterministic statistics, quality, and technical-analysis limits."""
    return service.get_chart(ticker, timeframe, country)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_asset_score(ticker: str, country: str = "") -> dict:
    """Get deterministic score axes, real metrics, valuation, risk ratios, warnings, and provenance."""
    return service.get_score(ticker, country)


@mcp.tool(annotations=READ_ONLY_TOOL)
def compare_assets(tickers: List[str], country: str = "") -> dict:
    """Compare up to 12 assets using the same quote, score, valuation, and risk contracts."""
    return service.compare_assets(tickers, country)


@mcp.tool(annotations=READ_ONLY_TOOL)
def list_sector_flow() -> dict:
    """List every sector's return, regional split, constituent count, and NORMAL/WATCH/ALERT signal."""
    return service.list_sectors()


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_sector_detail(sector: str, market: str = "all", limit: int = 20) -> dict:
    """Get sector performance, structural themes, intelligence, and leading constituents."""
    return service.get_sector(sector, market, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_market_movers(market: str = "id", mode: str = "gainers", limit: int = 8) -> dict:
    """Rank gainers, losers, top scores, or best risk/price assets for ID, US, crypto, others, or all."""
    return service.market_movers(market, mode, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def search_news(
    query: str = "", market: str = "all", category: str = "", sector: str = "", ticker: str = "",
    window_days: int = 7, must_read_only: bool = False, limit: int = 15,
) -> dict:
    """Search source-linked Intelligence Hub news with date, market, category, sector, ticker, and Must Read filters."""
    return service.search_news(query, market, category, sector, ticker, window_days, must_read_only, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_news_detail(url_or_title: str) -> dict:
    """Get one source-linked news record and its explicit summary basis by exact URL or title."""
    return service.get_news(url_or_title)


@mcp.tool(annotations=READ_ONLY_TOOL)
def search_videos(
    query: str = "", market: str = "all", category: str = "", channel: str = "", window_days: int = 7,
    must_watch_only: bool = False, include_knowledge: bool = False, limit: int = 15,
) -> dict:
    """Search Intelligence Hub videos and optionally Knowledge Hub episodes, including stored summaries."""
    return service.search_videos(query, market, category, channel, window_days, must_watch_only, include_knowledge, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_video_detail(video_id: str) -> dict:
    """Get one video's source, playback URLs, date, duration, priority, and available Cockpit summary."""
    return service.get_video(video_id)


@mcp.tool(annotations=READ_ONLY_TOOL)
def search_knowledge_hub(category: str = "all", query: str = "", limit: int = 20) -> dict:
    """Search Knowledge Hub episodes by category, show, title, host, or synthesized thesis."""
    return service.knowledge_hub(category, query, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def search_research(
    query: str = "", category: str = "", geography: str = "", ticker: str = "",
    publisher: str = "", publishers: Optional[List[str]] = None,
    date_from: str = "", date_to: str = "", year: Optional[int] = None,
    period: str = "", open_only: bool = False, limit: int = 20,
) -> dict:
    """Search the Cockpit research index by publishers, dates, period, category, geography, ticker, or access."""
    return service.search_research(query, category, geography, ticker, publisher, publishers,
                                   date_from, date_to, year, period, open_only, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def build_research_synthesis(
    query: str = "", category: str = "", geography: str = "", ticker: str = "",
    publisher: str = "", publishers: Optional[List[str]] = None,
    date_from: str = "", date_to: str = "", year: Optional[int] = None,
    period: str = "", open_only: bool = False, limit: int = 50,
) -> dict:
    """Mandatory first tool for cross-firm, H1/H2, annual-outlook, or consensus research requests."""
    return service.research_synthesis(query, category, geography, ticker, publisher, publishers,
                                      date_from, date_to, year, period, open_only, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_research_detail(id_or_url_or_title: str) -> dict:
    """Get one research record with publisher, evidence basis, access status, and original source links."""
    return service.get_research(id_or_url_or_title)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_company_evidence(ticker: str, market: str = "id", window_days: int = 7) -> dict:
    """Mandatory first tool for company analysis; use its chart evidence instead of scraping the dashboard."""
    return service.company_evidence(ticker, market, window_days)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_daily_brief() -> dict:
    """Get sentiment, synthesis, key themes, Must Read, Must Watch, and quality audit."""
    return service.daily_brief()


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_market_sentiment() -> dict:
    """Get Indonesia, US, global, and crypto sentiment plus the news and video digests."""
    return service.market_sentiment()


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_macro_analysis() -> dict:
    """Get source-linked macro analysis and cross-market arbiter context."""
    return service.macro_analysis()


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_active_alerts() -> dict:
    """Get current active alerts with descriptions and source links."""
    return service.active_alerts()


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_ipo_radar(view: str = "scheduled", market: str = "all", limit: int = 25) -> dict:
    """Get scheduled, pipeline/filed, recent-one-year, or S&P 500 change records with source health."""
    return service.ipo_radar(view, market, limit)


@mcp.tool(annotations=READ_ONLY_TOOL)
def get_intelligence_brief(
    topic: str = "", ticker: str = "", sector: str = "", market: str = "all", window_days: int = 3,
) -> dict:
    """Assemble grounded market data, sentiment, news, videos, research, macro analysis, and alerts for one question."""
    return service.intelligence_brief(topic, ticker, sector, market, window_days)


@mcp.resource("cockpit://status")
def status_resource() -> str:
    """Current Cockpit contract and source health."""
    import json
    return json.dumps(service.status(), ensure_ascii=False)


@mcp.resource("cockpit://daily-brief")
def daily_brief_resource() -> str:
    """Latest scheduled Daily Brief."""
    import json
    return json.dumps(service.daily_brief(), ensure_ascii=False)


@mcp.resource("cockpit://schema")
def schema_resource() -> str:
    """Cockpit data contracts and provenance rules."""
    import json
    return json.dumps(service.schema(), ensure_ascii=False)


@mcp.prompt()
def market_intelligence_question(question: str, market: str = "Indonesia") -> str:
    """Ground a market question in Cockpit's structured and cross-media evidence."""
    return (
        "Answer this market question using Project Cockpit tools: %s\n"
        "Primary market: %s. Start with cockpit_status, then use exact asset/sector tools and "
        "get_intelligence_brief. For a ticker, call get_company_evidence, get_asset_chart, and "
        "get_asset_score. For cross-firm research call build_research_synthesis first. Cite news, video, and "
        "research URLs. Distinguish provider facts, Cockpit calculations, publisher opinions, "
        "and your inference. State timestamp, market status, data quality, and missing fields. "
        "Do not inspect the dashboard UI for exposed data or invent fundamentals, targets, transcripts, or causal claims." % (question, market)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Project Cockpit MCP server")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"),
                        default=os.getenv("COCKPIT_MCP_TRANSPORT", "stdio"))
    parser.add_argument("--host", default=os.getenv("COCKPIT_MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("COCKPIT_MCP_PORT", "8790")))
    parser.add_argument("--data-dir", default=os.getenv("COCKPIT_DATA_DIR", ""))
    args = parser.parse_args()
    if args.data_dir:
        global service
        service = CockpitService(args.data_dir)
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
