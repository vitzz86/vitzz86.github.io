const CONTRACTS = ["data.json", "scores.json", "charts.json"];
const MARKET_ALIASES = {
  id: "ID", idx: "ID", indonesia: "ID",
  us: "US", usa: "US", sp500: "US", nasdaq: "US",
  crypto: "CR", cr: "CR", global: "ALL", all: "ALL", others: "OTHERS",
};

const clean = value => String(value ?? "")
  .replace(/<[^>]+>/g, " ")
  .replace(/&amp;/g, "&")
  .replace(/&lt;/g, "<")
  .replace(/&gt;/g, ">")
  .replace(/&quot;/g, '"')
  .replace(/&#39;/g, "'")
  .replace(/\s+/g, " ").trim();
const norm = value => clean(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const tokens = value => norm(value).split(" ").filter(token => token.length > 1);
const finite = value => Number.isFinite(Number(value)) ? Number(value) : null;
const marketCode = value => MARKET_ALIASES[String(value || "all").toLowerCase()] || String(value || "ALL").toUpperCase();
const limitOf = (value, fallback = 10, max = 50) => Math.max(1, Math.min(max, Number.parseInt(value, 10) || fallback));
const iso = value => finite(value) === null ? null : new Date(Number(value) * 1000).toISOString();
const titleKey = value => tokens(value).join(" ");

async function fetchJson(url, ttl = 30) {
  const response = await fetch(url, {
    headers: { Accept: "application/json", "User-Agent": "project-cockpit-remote-mcp/1.0" },
    cf: { cacheEverything: true, cacheTtl: ttl },
  });
  if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
  const data = await response.json();
  if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error(`${url} returned an invalid contract`);
  return data;
}

function createContractLoader(env) {
  const base = String(env.COCKPIT_DATA_BASE_URL || "https://vitzz86.github.io").replace(/\/$/, "");
  const pending = new Map();
  const loadOne = name => {
    if (!pending.has(name)) pending.set(name, fetchJson(`${base}/${name}`, 30));
    return pending.get(name);
  };
  return async (needs = []) => {
    const requested = [...new Set(["data.json", ...needs])];
    const values = await Promise.all(requested.map(loadOne));
    const loaded = Object.fromEntries(requested.map((name, index) => [name, values[index]]));
    return {
      data: loaded["data.json"],
      scores: loaded["scores.json"]?.scores || {},
      charts: loaded["charts.json"]?.charts || {},
      base,
    };
  };
}

function buildAssets(data, scores = {}, charts = {}) {
  const rows = [];
  const seen = new Set();
  for (const sector of data.sectors || []) {
    for (const original of sector.constituents || []) {
      const row = { ...original };
      row.sector_key ||= sector.key;
      row.sector_name ||= sector.name;
      const ref = row.score_ref || row.chart_ref || `${row.country}|${row.ticker}|${sector.key}`;
      if (seen.has(ref)) continue;
      seen.add(ref);
      row._ref = ref;
      row._score = scores[row.score_ref || ref] || row.fundamental_score || {};
      row._chart = charts[row.chart_ref || ref] || {};
      rows.push(row);
    }
  }
  return rows;
}

async function fastQuoteMap(data, env) {
  const base = String(data?.config?.idx_fast_quote_url || "").replace(/\/$/, "");
  if (!base) return { quotes: new Map(), health: { connected: false, reason: "gateway_not_configured" } };
  try {
    let payload;
    if (env?.IDX_QUOTES?.fetch) {
      const response = await env.IDX_QUOTES.fetch("https://idx-quotes.internal/quotes?market=idx", {
        headers: { Accept: "application/json", "User-Agent": "project-cockpit-remote-mcp/1.0" },
      });
      if (!response.ok) throw new Error(`IDX quote service binding returned HTTP ${response.status}`);
      payload = await response.json();
    } else {
      payload = await fetchJson(`${base}/quotes?market=idx`, 15);
    }
    const map = new Map((payload.quotes || []).map(item => [String(item.ticker || "").toUpperCase(), item]));
    return { quotes: map, health: { connected: true, as_of: iso(payload.asof), count: map.size, source: payload.source, mode: payload.quote_mode, connection: env?.IDX_QUOTES?.fetch ? "service_binding" : "public_gateway" } };
  } catch (error) {
    return { quotes: new Map(), health: { connected: false, reason: clean(error?.message) } };
  }
}

function withFastQuote(row, quotes) {
  if (row.country !== "ID") return row;
  const quote = quotes.get(String(row.ticker || "").toUpperCase());
  if (!quote) return row;
  return {
    ...row,
    value: finite(quote.price) ?? row.value,
    delta_pct: finite(quote.change_percent) ?? row.delta_pct,
    volume: finite(quote.volume) ?? row.volume,
    market_cap_value: finite(quote.market_cap) ?? row.market_cap_value,
    quote_asof: finite(quote.asof) ?? row.quote_asof,
    quote_mode: quote.quote_mode || "near_realtime_snapshot",
    source_name: quote.source || row.source_name,
    _live_overlay: true,
  };
}

function scoreSummary(score) {
  if (!score || score.score === undefined || score.score === null) return null;
  return {
    score: score.score, label: score.label, mode: score.mode, confidence: score.confidence,
    coverage: score.input_coverage ?? score.coverage, axes: score.axes || [], as_of: score.as_of,
    source: score.source, warnings: score.data_warnings || [],
  };
}

function assetView(row) {
  return {
    ticker: row.ticker, name: row.name, source_symbol: row.source_symbol,
    country: row.country, country_name: row.country_name, exchange: row.exchange,
    sector: row.sector_key, industry: row.industry, price: row.value,
    return_24h_pct: row.delta_pct, market_cap: row.market_cap_value,
    market_cap_display: row.mktcap, volume: row.volume, market_state: row.state,
    quote_as_of: iso(row.quote_asof), quote_mode: row.quote_mode,
    live_overlay: Boolean(row._live_overlay), data_tier: row.data_tier,
    source: { name: row.source_name || row.source_provider, url: row.source_url || row.url },
    interactive_chart_url: row.source_url || row.url,
    chart_quality: row.chart_quality || {}, score: scoreSummary(row._score), reference: row._ref,
  };
}

function resolveAsset(rows, ticker, country = "") {
  const wanted = String(ticker || "").trim().toUpperCase();
  let candidates = rows.filter(row => {
    const symbols = [row.ticker, row.source_symbol, String(row.source_symbol || "").replace(/\.JK$/, "")]
      .map(value => String(value || "").toUpperCase());
    return symbols.includes(wanted);
  });
  const code = country ? marketCode(country) : "ALL";
  if (code !== "ALL") candidates = candidates.filter(row => row.country === code || row.region === code);
  if (candidates.length === 1) return { row: candidates[0], candidates };
  candidates.sort((a, b) => (a.country === "ID" ? -1 : 1) - (b.country === "ID" ? -1 : 1) || (finite(b.market_cap_value) || 0) - (finite(a.market_cap_value) || 0));
  return { row: candidates.length ? candidates[0] : null, candidates };
}

function publicNews(item, mustRead = false) {
  const summary = clean(item.summary);
  return {
    title: clean(item.title), source: clean(item.source), published_at: iso(item.ts), market: item.geo,
    category: item.category, sectors: item.sectors || [], url: item.url, relevance_score: item.score,
    source_tier: item.source_tier || "unranked", must_read: mustRead, summary: summary || null,
    summary_basis: summary ? "publisher excerpt" : "headline and metadata only",
  };
}

function publicVideo(item, mustWatch = false) {
  const summary = clean(item.summary || item.thesis);
  return {
    video_id: item.video_id, title: clean(item.title), channel: clean(item.channel || item.show),
    published_at: item.published || iso(item.ts), market: item.geo, category: item.category,
    duration_seconds: item.duration_s, url: item.url, embed_url: item.embed,
    thumbnail_url: item.thumb, must_watch: mustWatch, summary: summary || null,
    summary_basis: summary ? "stored Cockpit synthesis" : "title and metadata only",
    collection: item._collection || "intelligence_hub",
  };
}

function publicResearch(item) {
  return {
    id: item.id, title: clean(item.title), publisher: clean(item.publisher),
    published: item.published || null, priority: item.priority, category: item.category,
    report_type: item.report_type || item.category, category_detail: item.category_detail,
    subcategory: item.subcategory, geography: item.geography, geography_detail: item.geography_detail,
    coverage: clean(item.coverage),
    access: item.access, format: item.format, ticker_tags: item.ticker_tags || [],
    sector_tags: item.sector_tags || [], why_useful: clean(item.why_useful) || null,
    direct_url: item.direct_url || null, landing_url: item.landing_url || null,
    source_url: item.source_url || item.direct_url || item.landing_url,
    source_type: item.source_type, verification: item.verification,
    verified_on: item.verified_on, summary_basis: item.summary_basis || "source metadata only",
  };
}

function mustReadKeys(data) {
  const urls = new Set(); const titles = new Set();
  for (const wrapper of data.daily_brief?.must_read || []) {
    const item = wrapper?.news;
    if (!item) continue;
    if (item.url) urls.add(item.url);
    titles.add(titleKey(item.title));
  }
  return { urls, titles };
}

function mustWatchIds(data) {
  return new Set((data.daily_brief?.must_watch || []).map(wrapper => wrapper?.video?.video_id).filter(Boolean));
}

function timeframePoints(row, timeframe) {
  const chart = row._chart || {};
  const tf = String(timeframe || "1M").toUpperCase();
  if (tf === "24H") {
    const values = (chart.intraday || []).map(finite).filter(value => value !== null);
    const end = finite(row.chart_asof) || finite(row.quote_asof) || Math.floor(Date.now() / 1000);
    const step = values.length > 1 ? Math.max(60, Math.floor(86400 / (values.length - 1))) : 300;
    return values.map((value, index) => ({ ts: end - step * (values.length - 1 - index), value }));
  }
  const days = { "1W": 7, "1M": 31, "3M": 93, "6M": 190 }[tf] || 31;
  const values = chart.spark || [];
  const stamps = chart.spark_ts || [];
  const paired = values.map((value, index) => ({ ts: finite(stamps[index]), value: finite(value) }))
    .filter(point => point.ts !== null && point.value !== null);
  if (!paired.length) return [];
  const cutoff = paired[paired.length - 1].ts - days * 86400;
  return paired.filter(point => point.ts >= cutoff).slice(-190);
}

function toolResponse(value) {
  return { content: [{ type: "text", text: JSON.stringify(value) }] };
}

function boundedHealth(data) {
  const intelligence = data.intelligence_health || {};
  const news = intelligence.news || {};
  const videos = intelligence.videos || {};
  const brief = intelligence.daily_brief || {};
  const source = data.coverage_universe?.source_health || {};
  return {
    sources: {
      idx: source.idx_all || {},
      charts: source.charts || {},
    },
    intelligence: {
      news: {
        wire_count: news.wire_count,
        geo: news.geo || {},
        category: news.category || {},
        trusted_items: news.trusted_items,
        wire_quality_failure_count: news.wire_quality_failure_count,
        sector_quality_failure_count: news.sector_quality_failure_count,
        sectors_below_3: news.sectors_below_3 || [],
        tickers_with_news: news.tickers_with_news,
        missing_ticker_count: news.missing_ticker_count,
        stale_ticker_count: news.stale_ticker_count,
        ticker_queries: news.ticker_queries,
        ticker_query_budget: news.ticker_query_budget,
        top_sources: news.top_sources || {},
      },
      videos: {
        video_count: videos.video_count,
        fresh_this_run: videos.fresh_this_run,
        source_total: videos.source_total,
        sources_present: videos.sources_present,
        missing_sources: videos.missing_sources || [],
        category: videos.category || {},
        geo: videos.geo || {},
      },
      daily_brief: brief,
    },
  };
}

export function createCockpitService(env) {
  const loadContracts = createContractLoader(env);
  let fastQuotesPromise;
  const loadFastQuotes = data => {
    if (!fastQuotesPromise) fastQuotesPromise = fastQuoteMap(data, env);
    return fastQuotesPromise;
  };

  return {
    toolResponse,

    async status() {
      const { data, base } = await loadContracts();
      const rows = buildAssets(data);
      const fast = await loadFastQuotes(data);
      const ageSeconds = data.timestamp ? Math.max(0, Math.floor((Date.now() - Date.parse(data.timestamp)) / 1000)) : null;
      return {
        service: "Project Cockpit MCP", mode: "read_only", transport: "streamable_http",
        payload_timestamp: data.timestamp, payload_age_seconds: ageSeconds,
        freshness: ageSeconds === null ? "unknown" : ageSeconds <= 3600 ? "fresh" : "stale",
        asset_count: rows.length, news_count: (data.news || []).length, video_count: (data.videos || []).length,
        knowledge_count: (data.podcasts || []).length, research_count: (data.research?.reports || []).length, data_source: base,
        dashboard_url: env.COCKPIT_DASHBOARD_URL || `${base}/cockpit.html`,
        idx_fast_quotes: fast.health, contracts: CONTRACTS,
        ...boundedHealth(data),
      };
    },

    async telemetry(symbol = "", includeChart = false) {
      const { data } = await loadContracts();
      const wanted = String(symbol || "").toUpperCase();
      const results = (data.telemetry || []).filter(item => !wanted || [item.symbol, item.label].map(v => String(v || "").toUpperCase()).includes(wanted))
        .map(item => ({
          symbol: item.symbol, label: item.label, kind: item.kind, value: item.value, value_unit: item.value_unit,
          return_24h_pct: item.delta_pct, previous_close: item.prev_close, market_state: item.state,
          quote_as_of: iso(item.quote_asof), quote_mode: item.quote_mode, source_url: item.url,
          chart_quality: item.chart_quality || {}, ...(includeChart ? { chart: item.spark || [], chart_timestamps: item.spark_ts || [], intraday: item.intraday || [] } : {}),
        }));
      return { as_of: data.timestamp, results };
    },

    async heatmap(market = "id", sector = "", limit = 120) {
      const { data } = await loadContracts();
      const fast = await loadFastQuotes(data);
      const code = marketCode(market); const wantedSector = norm(sector).replace(/ /g, "_");
      let rows = buildAssets(data).map(row => withFastQuote(row, fast.quotes)).filter(row => {
        const marketOk = code === "ALL" || row.country === code || row.region === code || (code === "US" && row.country === "US");
        return marketOk && (!wantedSector || norm(row.sector_key).replace(/ /g, "_") === wantedSector);
      });
      rows.sort((a, b) => (finite(b.market_cap_value) || 0) - (finite(a.market_cap_value) || 0));
      const cap = limitOf(limit, 120, 250);
      const results = rows.slice(0, cap).map(assetView);
      const bySector = {};
      for (const row of rows) bySector[row.sector_key || "other"] = (bySector[row.sector_key || "other"] || 0) + 1;
      return { as_of: data.timestamp, market: code, sector: sector || null, total_matches: rows.length, results, by_sector: bySector, idx_fast_quotes: fast.health };
    },

    async trending(market = "all", mode = "all") {
      const { data } = await loadContracts();
      const key = String(market || "all").toLowerCase();
      const block = data.trending?.[key] || data.trending || {};
      const results = mode === "all" ? block : block?.[mode] || [];
      return { as_of: data.timestamp, market: key, mode, results };
    },

    async searchAssets(query = "", market = "all", sector = "", limit = 15) {
      const { data, scores } = await loadContracts(["scores.json"]);
      const fast = await loadFastQuotes(data); const code = marketCode(market);
      const wantedSector = norm(sector).replace(/ /g, "_"); const q = tokens(query);
      let rows = buildAssets(data, scores).map(row => withFastQuote(row, fast.quotes)).filter(row => {
        if (code !== "ALL" && row.country !== code && row.region !== code) return false;
        if (wantedSector && norm(row.sector_key).replace(/ /g, "_") !== wantedSector) return false;
        const haystack = norm([row.ticker, row.name, row.industry, row.sector_name, row.country_name].join(" "));
        return !q.length || q.every(token => haystack.includes(token));
      });
      rows.sort((a, b) => (finite(b.market_cap_value) || 0) - (finite(a.market_cap_value) || 0));
      return { as_of: data.timestamp, query, market: code, sector: sector || null, total_matches: rows.length, results: rows.slice(0, limitOf(limit, 15)).map(assetView) };
    },

    async asset(ticker, country = "") {
      const { data, scores } = await loadContracts(["scores.json"]);
      const fast = await loadFastQuotes(data); const rows = buildAssets(data, scores);
      const resolved = resolveAsset(rows, ticker, country);
      if (!resolved.row) return { status: "not_found", ticker, candidates: resolved.candidates.slice(0, 10).map(assetView) };
      return { status: "ok", as_of: data.timestamp, ...assetView(withFastQuote(resolved.row, fast.quotes)), idx_fast_quotes: fast.health };
    },

    async chart(ticker, timeframe = "1M", country = "") {
      const { data, charts } = await loadContracts(["charts.json"]);
      const fast = await loadFastQuotes(data); const rows = buildAssets(data, {}, charts);
      const resolved = resolveAsset(rows, ticker, country);
      if (!resolved.row) return { status: "not_found", ticker };
      const row = withFastQuote(resolved.row, fast.quotes); let points = timeframePoints(row, timeframe);
      if (row.country === "ID" && row._live_overlay && points.length) {
        const last = points[points.length - 1];
        if (finite(row.quote_asof) > finite(last.ts)) points.push({ ts: finite(row.quote_asof), value: finite(row.value) });
      }
      const quality = row.chart_quality?.[String(timeframe || "1M").toUpperCase()] || (points.length ? "historical_points" : "unavailable");
      return {
        status: points.length ? "ok" : "unavailable", as_of: data.timestamp, ticker: row.ticker,
        timeframe: String(timeframe || "1M").toUpperCase(), point_count: points.length, points,
        chart_quality: quality, quote_as_of: iso(row.quote_asof), quote_mode: row.quote_mode,
        current_price: row.value, source: row.source_name || row.source_provider,
        interactive_chart_url: row.source_url || row.url,
        note: "Interactive charts open at the provider link; returned points are the auditable Cockpit chart contract.",
      };
    },

    async score(ticker, country = "") {
      const { data, scores } = await loadContracts(["scores.json"]);
      const rows = buildAssets(data, scores); const resolved = resolveAsset(rows, ticker, country);
      if (!resolved.row) return { status: "not_found", ticker };
      const score = resolved.row._score || {};
      if (!score.score && score.score !== 0) return { status: "unavailable", ticker: resolved.row.ticker, mode: "price_only", warnings: ["No validated score is available."] };
      return { status: "ok", as_of: data.timestamp, ticker: resolved.row.ticker, ...score };
    },

    async compare(tickers, country = "") {
      const selected = [...new Set((tickers || []).map(v => String(v).toUpperCase()))].slice(0, 12);
      const results = await Promise.all(selected.map(ticker => this.asset(ticker, country)));
      return { tickers: selected, results };
    },

    async sectors() {
      const { data } = await loadContracts();
      return { as_of: data.timestamp, results: (data.sectors || []).map(item => ({ key: item.key, name: item.name, return_pct: item.change, indonesia_return_pct: item.idChange, us_return_pct: item.usChange, signal: item.signal, constituent_count: (item.constituents || []).length })) };
    },

    async sector(sector, market = "all", limit = 20) {
      const { data, scores } = await loadContracts(["scores.json"]); const wanted = norm(sector).replace(/ /g, "_");
      const match = (data.sectors || []).find(item => [item.key, item.name].map(v => norm(v).replace(/ /g, "_")).includes(wanted));
      if (!match) return { status: "not_found", sector, available: (data.sectors || []).map(item => item.key) };
      const code = marketCode(market); const fast = await loadFastQuotes(data);
      const refs = new Map(buildAssets(data, scores).map(row => [row._ref, row]));
      const rows = (match.constituents || []).map(raw => refs.get(raw.score_ref || raw.chart_ref) || { ...raw, _score: raw.fundamental_score || {}, _ref: raw.score_ref || raw.chart_ref })
        .filter(row => code === "ALL" || row.country === code || row.region === code)
        .map(row => withFastQuote(row, fast.quotes)).sort((a, b) => (finite(b.market_cap_value) || 0) - (finite(a.market_cap_value) || 0));
      return { status: "ok", as_of: data.timestamp, key: match.key, name: match.name, signal: match.signal, return_pct: match.change, regional_returns: { indonesia: match.idChange, us: match.usChange }, structural_themes: match.themes || [], actionable_intelligence: clean(match.ai), total_constituents: rows.length, constituents: rows.slice(0, limitOf(limit, 20)).map(assetView) };
    },

    async movers(market = "id", mode = "gainers", limit = 8) {
      const { data, scores } = await loadContracts(["scores.json"]); const fast = await loadFastQuotes(data); const code = marketCode(market);
      let rows = buildAssets(data, scores).map(row => withFastQuote(row, fast.quotes)).filter(row => code === "ALL" || row.country === code || row.region === code);
      const requested = String(mode || "gainers").toLowerCase();
      if (requested === "top_score") rows = rows.filter(row => finite(row._score?.score) !== null).sort((a, b) => finite(b._score.score) - finite(a._score.score));
      else if (["best_risk_price", "best_value"].includes(requested)) rows = rows.filter(row => finite(row._score?.score) !== null).sort((a, b) => {
        const ar = finite((a._score.axes || []).find(x => x.key === "risk")?.score) || 0; const av = finite((a._score.axes || []).find(x => x.key === "value")?.score) || 0;
        const br = finite((b._score.axes || []).find(x => x.key === "risk")?.score) || 0; const bv = finite((b._score.axes || []).find(x => x.key === "value")?.score) || 0;
        return (br + bv) - (ar + av);
      });
      else rows = rows.filter(row => finite(row.delta_pct) !== null).sort((a, b) => requested === "losers" ? finite(a.delta_pct) - finite(b.delta_pct) : finite(b.delta_pct) - finite(a.delta_pct));
      return { as_of: data.timestamp, market: code, mode: requested, results: rows.slice(0, limitOf(limit, 8)).map(assetView), idx_fast_quotes: fast.health };
    },

    async news(args = {}) {
      const { data } = await loadContracts(); const code = marketCode(args.market); const wantedCategory = norm(args.category).replace(/ /g, "_"); const wantedSector = norm(args.sector).replace(/ /g, "_"); const query = tokens(args.query);
      let items = args.ticker ? data.ticker_news?.[String(args.ticker).toUpperCase()] || [] : data.news || [];
      const { urls, titles } = mustReadKeys(data); const anchor = Math.max(...items.map(item => finite(item.ts) || 0), Date.now() / 1000); const days = Math.max(1, Math.min(7, Number(args.window_days) || 7)); const cutoff = anchor - days * 86400;
      const seen = new Set(); const ranked = [];
      for (const item of items) {
        const identity = item.url || titleKey(item.title); if (!identity || seen.has(identity)) continue; seen.add(identity);
        const must = urls.has(item.url) || titles.has(titleKey(item.title));
        if (args.must_read_only && !must) continue; if ((finite(item.ts) || 0) < cutoff) continue; if (code !== "ALL" && item.geo !== code) continue;
        if (wantedCategory && norm(item.category).replace(/ /g, "_") !== wantedCategory) continue;
        if (wantedSector && !(item.sectors || []).map(v => norm(v).replace(/ /g, "_")).includes(wantedSector)) continue;
        const haystack = norm([item.title, item.summary, item.source, item.query].join(" ")); if (query.length && !query.every(token => haystack.includes(token))) continue;
        ranked.push({ item, must, rank: (must ? 10000 : 0) + (finite(item.score) || 0) + (finite(item.ts) || 0) / 1e6 });
      }
      ranked.sort((a, b) => b.rank - a.rank);
      return { as_of: data.timestamp, query: args.query || "", market: code, category: args.category || null, sector: args.sector || null, ticker: args.ticker || null, window_days: days, total_matches: ranked.length, results: ranked.slice(0, limitOf(args.limit, 15)).map(({ item, must }) => publicNews(item, must)), grounding_note: "Items without a stored summary are headline-and-metadata evidence only." };
    },

    async newsDetail(urlOrTitle) {
      const { data } = await loadContracts(); const wanted = String(urlOrTitle || ""); const key = titleKey(wanted); const must = mustReadKeys(data);
      const pool = [...(data.news || []), ...Object.values(data.ticker_news || {}).flat()]; const seen = new Set();
      for (const item of pool) {
        const identity = item.url || titleKey(item.title); if (!identity || seen.has(identity)) continue; seen.add(identity);
        if (item.url === wanted || titleKey(item.title) === key) return { status: "ok", as_of: data.timestamp, news: publicNews(item, must.urls.has(item.url) || must.titles.has(titleKey(item.title))) };
      }
      return { status: "not_found", query: wanted };
    },

    async videos(args = {}) {
      const { data } = await loadContracts(); const code = marketCode(args.market); const mustIds = mustWatchIds(data);
      let items = (data.videos || []).map(item => ({ ...item, _collection: "intelligence_hub" }));
      if (args.include_knowledge) items.push(...(data.podcasts || []).map(item => ({ ...item, _collection: "knowledge_hub", channel: item.show, summary: item.thesis })));
      const anchor = Math.max(...items.map(item => finite(item.ts) || 0), Date.now() / 1000); const days = Math.max(1, Math.min(7, Number(args.window_days) || 7)); const cutoff = anchor - days * 86400;
      const q = tokens(args.query); const category = norm(args.category).replace(/ /g, "_"); const channel = norm(args.channel); const seen = new Set(); const ranked = [];
      for (const item of items) {
        const id = item.video_id || item.url; if (!id || seen.has(id)) continue; seen.add(id); const must = mustIds.has(item.video_id);
        if (args.must_watch_only && !must) continue; if ((finite(item.ts) || 0) < cutoff) continue; if (code !== "ALL" && item.geo !== code) continue;
        if (category && norm(item.category).replace(/ /g, "_") !== category) continue; if (channel && !norm(item.channel || item.show).includes(channel)) continue;
        const haystack = norm([item.title, item.summary, item.thesis, item.channel, item.show, item.category].join(" ")); if (q.length && !q.every(token => haystack.includes(token))) continue;
        ranked.push({ item, must, rank: (must ? 10000 : 0) + (finite(item.ts) || 0) / 1e6 });
      }
      ranked.sort((a, b) => b.rank - a.rank);
      return { as_of: data.timestamp, query: args.query || "", market: code, category: args.category || null, channel: args.channel || null, window_days: days, include_knowledge: Boolean(args.include_knowledge), total_matches: ranked.length, results: ranked.slice(0, limitOf(args.limit, 15)).map(({ item, must }) => publicVideo(item, must)), grounding_note: "Stored summaries are Cockpit synthesis, not transcripts." };
    },

    async videoDetail(videoId) {
      const { data } = await loadContracts(); const must = mustWatchIds(data);
      for (const [collection, items] of [["intelligence_hub", data.videos || []], ["knowledge_hub", data.podcasts || []]]) {
        const original = items.find(item => item.video_id === videoId || item.url === videoId);
        if (!original) continue;
        const item = collection === "knowledge_hub" ? { ...original, _collection: collection, channel: original.show, summary: original.thesis } : { ...original, _collection: collection };
        return { status: "ok", as_of: data.timestamp, video: publicVideo(item, must.has(item.video_id)) };
      }
      return { status: "not_found", video_id: videoId };
    },

    async knowledge(category = "all", query = "", limit = 20) {
      const { data } = await loadContracts(); const wanted = norm(category).replace(/ /g, "_"); const q = tokens(query);
      const rows = (data.podcasts || []).filter(item => (wanted === "all" || wanted === norm(item.category).replace(/ /g, "_")) && (!q.length || q.every(token => norm([item.title, item.thesis, item.show, item.host].join(" ")).includes(token))))
        .sort((a, b) => (finite(b.ts) || 0) - (finite(a.ts) || 0));
      return { as_of: data.timestamp, category, total_matches: rows.length, results: rows.slice(0, limitOf(limit, 20)).map(item => publicVideo({ ...item, _collection: "knowledge_hub", channel: item.show, summary: item.thesis })) };
    },

    async research(args = {}) {
      const { data } = await loadContracts(); const q = tokens(args.query); const ticker = String(args.ticker || "").toUpperCase();
      const category = norm(args.category); const geography = norm(args.geography); const publisher = norm(args.publisher);
      const priorityRank = { essential: 0, high: 1, live: 2, supplementary: 3 };
      const rows = (data.research?.reports || []).filter(item => {
        if (category && !norm(item.category).includes(category)) return false;
        if (geography && !norm(item.geography).includes(geography)) return false;
        if (publisher && !norm(item.publisher).includes(publisher)) return false;
        if (ticker && !(item.ticker_tags || []).map(value => String(value).toUpperCase()).includes(ticker)) return false;
        if (args.open_only && !(/open|download|public/i.test(String(item.access || "")) || item.direct_url)) return false;
        const haystack = norm([item.title, item.publisher, item.category, item.subcategory, item.geography, item.why_useful, ...(item.ticker_tags || [])].join(" "));
        return !q.length || q.every(token => haystack.includes(token));
      }).sort((a, b) => (priorityRank[norm(a.priority)] ?? 4) - (priorityRank[norm(b.priority)] ?? 4) || (Date.parse(b.published || "") || 0) - (Date.parse(a.published || "") || 0));
      return { status: "ok", as_of: data.timestamp, query: args, total_matches: rows.length, results: rows.slice(0, limitOf(args.limit, 20)).map(publicResearch), synthesis: data.research?.synthesis || {}, health: data.research?.health || {}, grounding_note: data.research?.provenance_note };
    },

    async researchDetail(idOrUrlOrTitle) {
      const { data } = await loadContracts(); const wanted = String(idOrUrlOrTitle || ""); const key = titleKey(wanted);
      const item = (data.research?.reports || []).find(row => row.id === wanted || row.source_url === wanted || row.direct_url === wanted || row.landing_url === wanted || titleKey(row.title) === key);
      return item ? { status: "ok", as_of: data.timestamp, research: publicResearch(item), grounding_note: data.research?.provenance_note } : { status: "not_found", query: wanted };
    },

    async companyEvidence(ticker, market = "id", windowDays = 7) {
      const [asset, score, chart, news, videos, research] = await Promise.all([
        this.asset(ticker, market), this.score(ticker, market), this.chart(ticker, "6M", market),
        this.news({ ticker, market, window_days: windowDays, limit: 10 }),
        this.videos({ query: ticker, market, window_days: windowDays, include_knowledge: true, limit: 8 }),
        this.research({ query: ticker, ticker, limit: 12 }),
      ]);
      let contextResearch = [];
      if (!(research.results || []).length) {
        const code = marketCode(market);
        const geography = code === "ID" ? "Indonesia" : code === "US" ? "Global" : "";
        const sector = asset?.status === "ok" ? asset.sector : "";
        let context = await this.research({ query: sector, geography, limit: 6 });
        if (!(context.results || []).length && geography) context = await this.research({ geography, limit: 6 });
        contextResearch = context.results || [];
      }
      return { ticker: String(ticker).toUpperCase(), market: marketCode(market), asset, score, chart, news: news.results || [], videos: videos.results || [], research: research.results || [], context_research: contextResearch, provenance_rules: ["Provider data, Cockpit calculations, publisher research, and AI inference must be labelled separately.", "Broker opinions and target prices are evidence, not facts or personalized recommendations.", "Open the linked report before relying on a recommendation or valuation."] };
    },

    async dailyBrief() { const { data } = await loadContracts(); return { ...data.daily_brief, payload_timestamp: data.timestamp, provenance: "Cockpit scheduled synthesis; linked cards remain the evidence of record." }; },
    async sentiment() { const { data } = await loadContracts(); const brief = data.daily_brief || {}; return { as_of: data.timestamp, sentiment: brief.sentiment || {}, daily_synthesis: brief.synthesis, key_themes: brief.key_themes || [], news_digest: brief.news_digest || {}, video_digest: brief.video_digest || {} }; },
    async macro() { const { data } = await loadContracts(); return { as_of: data.timestamp, analysis: data.macro_analysis || [], arbiter_brief: data.arbiter_brief, source_policy: "Each point carries its source links." }; },
    async alerts() { const { data } = await loadContracts(); return { as_of: data.timestamp, alerts: data.alerts || [] }; },

    async ipo(view = "scheduled", market = "all", limit = 25) {
      const { data } = await loadContracts(); const ipo = data.ipo || {}; const aliases = { recent_1y: "recent", pipeline_filed: "pipeline", filed: "pipeline" }; const key = aliases[String(view || "scheduled").toLowerCase().replace(/ /g, "_")] || String(view || "scheduled").toLowerCase().replace(/ /g, "_");
      if (!["scheduled", "pipeline", "recent", "sp500_changes"].includes(key)) return { status: "invalid_view", allowed: ["scheduled", "pipeline", "recent", "sp500_changes"] };
      const code = marketCode(market); let rows = [];
      if (key === "sp500_changes") rows = [...(ipo.sp500_changes || [])];
      else {
        const map = { scheduled: ["upcoming_id", "upcoming_us"], pipeline: ["pipeline_id", "pipeline_us"], recent: ["recent_id", "recent_us"] }[key];
        if (["ALL", "ID"].includes(code)) rows.push(...(ipo[map[0]] || [])); if (["ALL", "US"].includes(code)) rows.push(...(ipo[map[1]] || []));
      }
      return { status: "ok", as_of: data.timestamp, view: key, market: code, total_matches: rows.length, results: rows.slice(0, limitOf(limit, 25)), synthesis: ipo.synthesis || {}, health: ipo.health || {}, note: ipo.note };
    },

    async intelligence(args = {}) {
      const query = args.topic || args.ticker || args.sector || "";
      const [status, asset, news, videos, research, sentiment, macro, alerts] = await Promise.all([
        this.status(), args.ticker ? this.asset(args.ticker, args.market) : null,
        this.news({ query, market: args.market, sector: args.sector, ticker: args.ticker, window_days: args.window_days, limit: 8 }),
        this.videos({ query, market: args.market, window_days: args.window_days, include_knowledge: true, limit: 8 }),
        this.research({ query, ticker: args.ticker, limit: 8 }),
        this.sentiment(), this.macro(), this.alerts(),
      ]);
      return { as_of: status.payload_timestamp, request: args, asset, sentiment, news: news.results || [], videos: videos.results || [], research: research.results || [], macro_analysis: macro.analysis || [], alerts: alerts.alerts || [], grounding_rules: ["Prefer exact ticker and source-linked evidence.", "News without summaries is headline-only evidence.", "Video summaries are Cockpit synthesis, not transcripts.", "Broker research is attributed opinion, not fact.", "State missing or stale data; never estimate absent fundamentals."] };
    },
  };
}
