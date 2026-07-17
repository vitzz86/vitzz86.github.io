const TV_SCAN_URL = "https://scanner.tradingview.com/indonesia/scan";
const TV_COLUMNS = ["name", "close", "change", "volume", "market_cap_basic"];
const CACHE_SECONDS = 30;

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function json(body, status = 200, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...cors, ...extra },
  });
}

function cleanTicker(value) {
  return String(value || "").split(":").pop().trim().toUpperCase();
}

async function tradingViewQuotes() {
  const response = await fetch(TV_SCAN_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "Origin": "https://www.tradingview.com",
      "Referer": "https://www.tradingview.com/",
      "User-Agent": "Mozilla/5.0 (Project Cockpit; IDX quote gateway)",
    },
    body: JSON.stringify({
      filter: [{ left: "type", operation: "equal", right: "stock" }],
      options: { lang: "en" },
      markets: ["indonesia"],
      symbols: { query: { types: [] }, tickers: [] },
      columns: TV_COLUMNS,
      sort: { sortBy: "market_cap_basic", sortOrder: "desc" },
      range: [0, 1200],
    }),
  });
  if (!response.ok) throw new Error(`TradingView ${response.status}`);
  const payload = await response.json();
  const asof = Math.floor(Date.now() / 1000);
  const quotes = (payload.data || []).map(row => {
    const values = row.d || [];
    const ticker = cleanTicker(values[0] || row.s);
    const price = Number(values[1]);
    const change = Number(values[2]);
    if (!ticker || !Number.isFinite(price)) return null;
    return {
      ticker,
      source_symbol: `${ticker}.JK`,
      country: "ID",
      price,
      change_percent: Number.isFinite(change) ? change : null,
      volume: Number.isFinite(Number(values[3])) ? Number(values[3]) : null,
      market_cap: Number.isFinite(Number(values[4])) ? Number(values[4]) : null,
      asof,
      quote_mode: "near_realtime_snapshot",
      source: "TradingView IDX snapshot",
    };
  }).filter(Boolean);
  return { asof, quote_mode: "near_realtime_snapshot", source: "TradingView", count: quotes.length, quotes };
}

async function quoteResponse(request) {
  const cache = caches.default;
  const cacheKey = new Request(new URL("/quotes?market=idx", request.url), request);
  const cached = await cache.match(cacheKey);
  if (cached) return cached;
  const body = await tradingViewQuotes();
  const response = json(body, 200, {
    "Cache-Control": `public, max-age=15, s-maxage=${CACHE_SECONDS}, stale-while-revalidate=30`,
  });
  await cache.put(cacheKey, response.clone());
  return response;
}

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "GET") return json({ error: "method_not_allowed" }, 405);
    const url = new URL(request.url);
    try {
      if (url.pathname === "/health") {
        return json({ ok: true, service: "project-cockpit-idx-quotes", mode: "near_realtime_snapshot" });
      }
      if (url.pathname === "/quotes" && (url.searchParams.get("market") || "idx") === "idx") {
        return await quoteResponse(request);
      }
      return json({ error: "not_found" }, 404);
    } catch (error) {
      return json({ error: "upstream_unavailable", detail: String(error && error.message || error) }, 502, {
        "Cache-Control": "no-store",
      });
    }
  },
};
