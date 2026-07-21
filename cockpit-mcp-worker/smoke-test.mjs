import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const url = process.env.COCKPIT_MCP_TEST_URL || "http://127.0.0.1:8791/mcp";
const token = process.env.COCKPIT_MCP_BEARER_TOKEN || "";
const transport = new StreamableHTTPClientTransport(new URL(url), {
  requestInit: token ? { headers: { Authorization: `Bearer ${token}` } } : undefined,
});
const client = new Client({ name: "project-cockpit-smoke-test", version: "1.0.0" });

try {
  await client.connect(transport);
  const tools = await client.listTools();
  if (tools.tools.length !== 28) throw new Error(`Expected 28 tools, received ${tools.tools.length}`);
  const status = await client.callTool({ name: "cockpit_status", arguments: {} });
  const asset = await client.callTool({ name: "get_asset", arguments: { ticker: "BBCA", country: "ID" } });
  const chart = await client.callTool({ name: "get_asset_chart", arguments: { ticker: "BBCA", country: "ID", timeframe: "1M" } });
  const videos = await client.callTool({ name: "search_videos", arguments: { market: "ID", limit: 2 } });
  const researchBundle = await client.callTool({ name: "build_research_synthesis", arguments: { publishers: ["BlackRock", "J.P. Morgan", "Morgan Stanley"], period: "H1 2026", limit: 20 } });
  const company = await client.callTool({ name: "get_company_evidence", arguments: { ticker: "BBCA", market: "ID", window_days: 7 } });
  const parse = result => JSON.parse(result.content.find(item => item.type === "text")?.text || "{}");
  const parsedStatus = parse(status); const parsedAsset = parse(asset); const parsedChart = parse(chart); const parsedVideos = parse(videos);
  const parsedResearch = parse(researchBundle); const parsedCompany = parse(company);
  if (!parsedStatus.payload_timestamp) throw new Error("Status has no payload timestamp");
  if (parsedAsset.status !== "ok" || parsedAsset.ticker !== "BBCA") throw new Error("BBCA lookup failed");
  if (parsedChart.status !== "ok" || parsedChart.point_count < 2) throw new Error("BBCA chart failed");
  if (!parsedChart.analysis_guardrails?.supported_analysis) throw new Error("Chart guardrails missing");
  if (parsedChart.analysis_guardrails.unsupported_analysis?.exact_support_resistance !== true) throw new Error("Chart precision guardrail missing");
  if (!parsedVideos.results?.length) throw new Error("Video search failed");
  if (!parsedResearch.coverage_audit || !parsedResearch.period?.date_from) throw new Error("Research synthesis audit failed");
  if (parsedResearch.synthesis_readiness?.source_open_required !== true) throw new Error("Research evidence-scope guardrail failed");
  if (parsedCompany.chart?.required_tool_call?.name !== "get_asset_chart") throw new Error("Company chart routing guardrail failed");
  const coverage = [
    ["get_market_telemetry", { symbol: "^JKSE" }],
    ["get_macro_indicators", { view: "core" }],
    ["get_macro_indicators", { view: "country_risk" }],
    ["get_market_heatmap", { market: "ID", limit: 3 }],
    ["get_trending_assets", { market: "id", mode: "all" }],
    ["search_assets", { query: "bank", market: "ID", limit: 3 }],
    ["get_asset_score", { ticker: "BBCA", country: "ID" }],
    ["compare_assets", { tickers: ["BBCA", "BBRI"], country: "ID" }],
    ["list_sector_flow", {}],
    ["get_sector_detail", { sector: "financials", market: "ID", limit: 3 }],
    ["get_market_movers", { market: "ID", mode: "gainers", limit: 3 }],
    ["search_news", { market: "ID", limit: 2 }],
    ["search_knowledge_hub", { category: "all", limit: 2 }],
    ["search_research", { geography: "Indonesia", limit: 2 }],
    ["get_daily_brief", {}],
    ["get_market_sentiment", {}],
    ["get_macro_analysis", {}],
    ["get_active_alerts", {}],
    ["get_ipo_radar", { view: "recent", market: "ID", limit: 2 }],
    ["get_intelligence_brief", { ticker: "BBCA", market: "ID", window_days: 7 }],
  ];
  let checked = 6;
  for (const [name, arguments_] of coverage) {
    const result = await client.callTool({ name, arguments: arguments_ });
    if (result.isError) throw new Error(`${name} returned an MCP error`);
    parse(result);
    checked += 1;
  }
  const firstNews = parse(await client.callTool({ name: "search_news", arguments: { market: "ID", limit: 1 } })).results?.[0];
  if (firstNews?.url) {
    parse(await client.callTool({ name: "get_news_detail", arguments: { url_or_title: firstNews.url } }));
    checked += 1;
  }
  const firstVideo = parsedVideos.results?.[0];
  if (firstVideo?.video_id) {
    parse(await client.callTool({ name: "get_video_detail", arguments: { video_id: firstVideo.video_id } }));
    checked += 1;
  }
  const firstResearch = parse(await client.callTool({ name: "search_research", arguments: { limit: 1 } })).results?.[0];
  if (firstResearch?.id) {
    parse(await client.callTool({ name: "get_research_detail", arguments: { id_or_url_or_title: firstResearch.id } }));
    checked += 1;
  }
  console.log(JSON.stringify({ url, tools: tools.tools.length, tool_calls_checked: checked, timestamp: parsedStatus.payload_timestamp, idx_fast_quotes: parsedStatus.idx_fast_quotes, bbca_live_overlay: parsedAsset.live_overlay, chart_points: parsedChart.point_count, video_results: parsedVideos.results.length }, null, 2));
} finally {
  await client.close();
}
