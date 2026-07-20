# Project Cockpit Remote MCP

Cloudflare Worker deployment of Project Cockpit's read-only MCP service. It
uses Streamable HTTP at `/mcp`, exposes the same 23 tools as the local Python
server, reads the live GitHub Pages contracts, and overlays the existing IDX
fast-quote gateway on current-price queries.

## Data behavior

- `data.json`, `scores.json`, and `charts.json` come from
  `https://vitzz86.github.io` and are edge-cached for 30 seconds.
- IDX asset, heatmap, sector, and mover queries call the configured TradingView
  snapshot Worker through a private Cloudflare service binding and use its
  newest quote when available.
- Historical chart points remain the audited Cockpit contracts. Each chart
  result includes the TradingView, Yahoo Finance, or CoinGecko interactive URL.
- Video results include YouTube watch and embed links plus the stored Cockpit
  synthesis when present.
- The Worker is read-only. It cannot place trades or modify the repository.

## Local verification

```bash
cd cockpit-mcp-worker
npm install
npm run dev
```

In another terminal:

```bash
cd cockpit-mcp-worker
npm run smoke
```

## Deployment

```bash
cd cockpit-mcp-worker
npx wrangler login
npm run deploy
```

The deployed production URLs are:

```text
https://project-cockpit-mcp.samudravito4.workers.dev/mcp
https://project-cockpit-mcp.samudravito4.workers.dev/health
```

`wrangler.toml` binds `IDX_QUOTES` directly to
`project-cockpit-idx-quotes`, avoiding a public Worker-to-Worker network hop.

The endpoint is intentionally authless by default because it exposes the same
public, read-only information as the dashboard. To require a bearer token:

```bash
npx wrangler secret put COCKPIT_MCP_BEARER_TOKEN
```

Static bearer authentication is suitable for clients that support custom
headers. ChatGPT custom connectors should use the authless endpoint initially;
Cloudflare Access OAuth can be added later for private multi-user access.

## Client URLs

- ChatGPT custom connector: use
  `https://project-cockpit-mcp.samudravito4.workers.dev/mcp` with no
  authentication, then refresh the connector to discover all 23 tools.
- Claude custom connector: use the same production `/mcp` URL with no
  authentication.
- Claude Desktop fallback:
  `npx mcp-remote https://project-cockpit-mcp.samudravito4.workers.dev/mcp`.
- Codex: register the production Streamable HTTP URL or retain the local Python
  server for offline access.

## Verification

```bash
COCKPIT_MCP_TEST_URL=https://project-cockpit-mcp.samudravito4.workers.dev/mcp npm run smoke
```

The smoke test discovers all 23 tools and exercises current quotes, charts,
scores, sectors, movers, news, videos, Knowledge Hub, Daily Brief, macro,
alerts, IPO radar, and the combined intelligence brief.
