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
  if (tools.tools.length !== 27) throw new Error(`Expected 27 tools, received ${tools.tools.length}`);
  const status = await client.callTool({ name: "cockpit_status", arguments: {} });
  const asset = await client.callTool({ name: "get_asset", arguments: { ticker: "BBCA", country: "ID" } });
  const chart = await client.callTool({ name: "get_asset_chart", arguments: { ticker: "BBCA", country: "ID", timeframe: "1M" } });
  const videos = await client.callTool({ name: "search_videos", arguments: { market: "ID", limit: 2 } });
  const parse = result => JSON.parse(result.content.find(item => item.type === "text")?.text || "{}");
  const parsedStatus = parse(status); const parsedAsset = parse(asset); const parsedChart = parse(chart); const parsedVideos = parse(videos);
  if (!parsedStatus.payload_timestamp) throw new Error("Status has no payload timestamp");
  if (parsedAsset.status !== "ok" || parsedAsset.ticker !== "BBCA") throw new Error("BBCA lookup failed");
  if (parsedChart.status !== "ok" || parsedChart.point_count < 2) throw new Error("BBCA chart failed");
  if (!parsedVideos.results?.length) throw new Error("Video search failed");
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
    ["get_company_evidence", { ticker: "BBCA", market: "ID", window_days: 7 }],
    ["get_daily_brief", {}],
    ["get_market_sentiment", {}],
    ["get_macro_analysis", {}],
    ["get_active_alerts", {}],
    ["get_ipo_radar", { view: "recent", market: "ID", limit: 2 }],
    ["get_intelligence_brief", { ticker: "BBCA", market: "ID", window_days: 7 }],
  ];
  let checked = 4;
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
