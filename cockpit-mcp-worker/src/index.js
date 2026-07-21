import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { createMcpHandler } from "agents/mcp";
import { z } from "zod";
import { createCockpitService } from "./service.js";

const readOnly = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false };
const optionalString = z.string().optional();
const optionalLimit = z.number().int().min(1).max(50).optional();

function createServer(env) {
  const server = new McpServer({
    name: "Project Cockpit",
    version: "1.1.0",
  }, {
    instructions: "Project Cockpit is the first source for covered market, ticker, chart, score, news, video, IPO, macro, and research questions. Do not inspect or scrape the dashboard UI for data exposed by a Cockpit tool. For ticker analysis call get_company_evidence, then get_asset_chart and get_asset_score. Treat the score as a deterministic screening opinion, never as an investment recommendation: report the separate opportunity score, data-confidence percentage, factor weaknesses, valuation confidence, and limitations. Reconcile source-linked research that disagrees with the screen; never force external evidence to match Cockpit or another AI. For cross-firm or period research call build_research_synthesis before any generic workflow or web search. External browsing is gap-fill only: open indexed source_url records or find publishers explicitly reported missing. Always state timestamp, market state, provider, score mode, confidence, chart quality, and warnings when material. Distinguish provider facts, deterministic Cockpit calculations, attributed publisher opinions, and AI inference. Research metadata is discovery evidence, not report content. Exact technical levels, candlestick patterns, and volume confirmation require explicit OHLCV data. Never invent missing fundamentals, targets, transcripts, causal claims, transaction data, or recommendations.",
  });
  const service = createCockpitService(env);
  const tool = (name, description, schema, handler) => server.registerTool(name, {
    description,
    inputSchema: schema,
    annotations: readOnly,
  }, async input => service.toolResponse(await handler(input || {})));

  tool("cockpit_status", "Check live payload freshness, coverage, GitHub contract health, and IDX fast-quote connectivity.", {}, () => service.status());
  tool("get_market_telemetry", "Get indices, commodities, FX, crypto, and macro-rate telemetry.", { symbol: optionalString, include_chart: z.boolean().optional() }, ({ symbol, include_chart }) => service.telemetry(symbol, include_chart));
  tool("get_macro_indicators", "Get source-linked Indonesia macro releases, sovereign ratings, market classifications, and transparent market-derived country-risk measures. view accepts core, detail, ratings, or country_risk.", { view: z.enum(["core", "detail", "ratings", "country_risk"]).optional(), pillar: optionalString }, ({ view, pillar }) => service.macroIndicators(view, pillar));
  tool("get_market_heatmap", "Get market-cap-sized heatmap assets for Indonesia, US, crypto, or other markets.", { market: optionalString, sector: optionalString, limit: z.number().int().min(1).max(250).optional() }, ({ market, sector, limit }) => service.heatmap(market, sector, limit));
  tool("get_trending_assets", "Get baked gainers, losers, top-score, active, and social-trending signals.", { market: optionalString, mode: optionalString }, ({ market, mode }) => service.trending(market, mode));
  tool("search_assets", "Search the complete asset universe by ticker, company, industry, sector, or country.", { query: optionalString, market: optionalString, sector: optionalString, limit: optionalLimit }, ({ query, market, sector, limit }) => service.searchAssets(query, market, sector, limit));
  tool("get_asset", "Get one asset with current quote, market state, performance, liquidity, source, and score summary. IDX requests use the fast quote gateway when available.", { ticker: z.string().min(1), country: optionalString }, ({ ticker, country }) => service.asset(ticker, country));
  tool("get_asset_chart", "Primary chart-data tool. Get auditable points, deterministic trend/range/drawdown statistics, chart quality, and explicit technical-analysis limits for 24h, 1W, 1M, 3M, or 6M. Use this instead of browsing the dashboard UI.", { ticker: z.string().min(1), timeframe: z.enum(["24h", "24H", "1W", "1M", "3M", "6M"]).optional(), country: optionalString }, ({ ticker, timeframe, country }) => service.chart(ticker, timeframe, country));
  tool("get_asset_score", "Get the deterministic opportunity screen, separate data confidence, factor gates, real metrics, valuation scenarios, risk ratios, limitations, warnings, and provenance. This is a screening model, not an investment recommendation.", { ticker: z.string().min(1), country: optionalString }, ({ ticker, country }) => service.score(ticker, country));
  tool("compare_assets", "Compare up to 12 assets using consistent quote and score contracts.", { tickers: z.array(z.string()).min(1).max(12), country: optionalString }, ({ tickers, country }) => service.compare(tickers, country));
  tool("list_sector_flow", "List sector returns, regional splits, counts, and NORMAL/WATCH/ALERT signals.", {}, () => service.sectors());
  tool("get_sector_detail", "Get sector performance, structural themes, intelligence, and leading constituents.", { sector: z.string().min(1), market: optionalString, limit: optionalLimit }, ({ sector, market, limit }) => service.sector(sector, market, limit));
  tool("get_market_movers", "Rank gainers, losers, top scores, or best risk/value assets.", { market: optionalString, mode: z.enum(["gainers", "losers", "top_score", "best_risk_price", "best_value"]).optional(), limit: optionalLimit }, ({ market, mode, limit }) => service.movers(market, mode, limit));
  tool("search_news", "Search source-linked Intelligence Hub news by query, market, category, sector, ticker, date window, or Must Read.", { query: optionalString, market: optionalString, category: optionalString, sector: optionalString, ticker: optionalString, window_days: z.number().int().min(1).max(7).optional(), must_read_only: z.boolean().optional(), limit: optionalLimit }, input => service.news(input));
  tool("get_news_detail", "Get one exact source-linked news record and its summary basis.", { url_or_title: z.string().min(1) }, ({ url_or_title }) => service.newsDetail(url_or_title));
  tool("search_videos", "Search Intelligence Hub videos and optional Knowledge Hub episodes with stored summaries.", { query: optionalString, market: optionalString, category: optionalString, channel: optionalString, window_days: z.number().int().min(1).max(7).optional(), must_watch_only: z.boolean().optional(), include_knowledge: z.boolean().optional(), limit: optionalLimit }, input => service.videos(input));
  tool("get_video_detail", "Get one video's source, YouTube playback/embed URLs, date, duration, priority, and Cockpit summary.", { video_id: z.string().min(1) }, ({ video_id }) => service.videoDetail(video_id));
  tool("search_knowledge_hub", "Search Knowledge Hub episodes by category, show, title, host, or thesis.", { category: optionalString, query: optionalString, limit: optionalLimit }, ({ category, query, limit }) => service.knowledge(category, query, limit));
  tool("search_research", "Primary discovery tool for Project Cockpit's indexed institutional research. Filter by one or many publishers, date range, year, half-year period, category, geography, ticker, or access. Returns evidence scope and a coverage audit; indexed metadata must not be presented as full-report content.", { query: optionalString, category: optionalString, geography: optionalString, ticker: optionalString, publisher: optionalString, publishers: z.array(z.string()).max(25).optional(), date_from: optionalString, date_to: optionalString, year: z.number().int().min(2000).max(2100).optional(), period: optionalString, open_only: z.boolean().optional(), limit: optionalLimit }, input => service.research(input));
  tool("build_research_synthesis", "Mandatory first tool for cross-firm, multi-report, H1/H2, annual-outlook, or consensus research questions. Builds the Cockpit report inventory, publisher/date coverage audit, source-opening requirements, and synthesis contract before external gap-filling.", { query: optionalString, category: optionalString, geography: optionalString, ticker: optionalString, publisher: optionalString, publishers: z.array(z.string()).max(25).optional(), date_from: optionalString, date_to: optionalString, year: z.number().int().min(2000).max(2100).optional(), period: optionalString, open_only: z.boolean().optional(), limit: optionalLimit }, input => service.researchSynthesis(input));
  tool("get_research_detail", "Get one exact research record with publisher, date, evidence basis, access status, and original report links.", { id_or_url_or_title: z.string().min(1) }, ({ id_or_url_or_title }) => service.researchDetail(id_or_url_or_title));
  tool("get_company_evidence", "Mandatory first tool for company or ticker analysis. Builds an institutional evidence packet with live quote, deterministic score, liquidity/risk, news, videos, research, and the exact follow-up get_asset_chart call. Never substitute dashboard scraping for the follow-up chart tool.", { ticker: z.string().min(1), market: optionalString, window_days: z.number().int().min(1).max(7).optional() }, ({ ticker, market, window_days }) => service.companyEvidence(ticker, market, window_days));
  tool("get_daily_brief", "Get sentiment, synthesis, key themes, Must Read, Must Watch, and quality audit.", {}, () => service.dailyBrief());
  tool("get_market_sentiment", "Get Indonesia, US, global, and crypto sentiment plus news and video digests.", {}, () => service.sentiment());
  tool("get_macro_analysis", "Get source-linked macro analysis and cross-market context.", {}, () => service.macro());
  tool("get_active_alerts", "Get active alerts with descriptions and source links.", {}, () => service.alerts());
  tool("get_ipo_radar", "Get scheduled, pipeline/filed, recent-one-year, or S&P 500 change records.", { view: z.enum(["scheduled", "pipeline", "pipeline_filed", "filed", "recent", "recent_1y", "sp500_changes"]).optional(), market: optionalString, limit: optionalLimit }, ({ view, market, limit }) => service.ipo(view, market, limit));
  tool("get_intelligence_brief", "Assemble grounded market data, sentiment, news, videos, research, macro analysis, and alerts for one question.", { topic: optionalString, ticker: optionalString, sector: optionalString, market: optionalString, window_days: z.number().int().min(1).max(7).optional() }, input => service.intelligence(input));
  return server;
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

function authorized(request, env) {
  const expected = String(env.COCKPIT_MCP_BEARER_TOKEN || "").trim();
  if (!expected) return true;
  return request.headers.get("Authorization") === `Bearer ${expected}`;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      try {
        const service = createCockpitService(env);
        return json({ status: "ok", ...(await service.status()) });
      } catch (error) {
        return json({ status: "error", message: String(error?.message || error) }, 503);
      }
    }
    if (url.pathname === "/") {
      return json({ service: "Project Cockpit MCP", status: "online", mcp_endpoint: "/mcp", health_endpoint: "/health", dashboard: env.COCKPIT_DASHBOARD_URL });
    }
    if (url.pathname !== "/mcp") return json({ error: "not_found" }, 404);
    if (!authorized(request, env)) return json({ error: "unauthorized", message: "Valid bearer token required." }, 401);
    const server = createServer(env);
    return createMcpHandler(server, { route: "/mcp", enableJsonResponse: true })(request, env, ctx);
  },
};
