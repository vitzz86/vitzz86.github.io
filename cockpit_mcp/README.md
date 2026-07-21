# Project Cockpit MCP

Read-only Model Context Protocol server for the compiled Project Cockpit
contracts. It makes the dashboard queryable from Codex, Claude, ChatGPT, and
other Streamable HTTP or `stdio` MCP clients without moving calculations into
the chatbot.

## Coverage

The server reads the same three files as the dashboard:

- `data.json`: telemetry, sectors, Intelligence Hub, Knowledge Hub, Daily Brief,
  market sentiment, Macro Analysis, alerts, IPO radar, research, source health.
- `scores.json`: deterministic score axes, provider metrics, validation warnings,
  valuation, liquidity, and risk statistics.
- `charts.json`: 24h, 1W, 1M, 3M, and 6M chart points with quality labels.

The server exposes 27 bounded tools:

| Area | Tools |
|---|---|
| Health | `cockpit_status` |
| Overview | `get_market_telemetry`, `get_macro_indicators`, `get_market_heatmap`, `get_trending_assets` |
| Assets | `search_assets`, `get_asset`, `get_asset_chart`, `get_asset_score`, `compare_assets` |
| Markets | `list_sector_flow`, `get_sector_detail`, `get_market_movers` |
| Intelligence Hub | `search_news`, `get_news_detail`, `search_videos`, `get_video_detail`, `get_daily_brief`, `get_market_sentiment` |
| Knowledge Hub | `search_knowledge_hub` |
| Research | `search_research`, `get_research_detail`, `get_company_evidence` |
| Analysis | `get_macro_analysis`, `get_active_alerts`, `get_intelligence_brief` |
| Listings | `get_ipo_radar` |

It also publishes:

- Resources: `cockpit://status`, `cockpit://daily-brief`, `cockpit://schema`
- Prompt: `market_intelligence_question`

## Grounding rules

- Every response uses the timestamp and provenance already stored by Cockpit.
- Missing fundamentals are returned as missing, never estimated.
- News without a stored excerpt is labelled `headline and metadata only`.
- A video summary is labelled `stored Cockpit synthesis`; it is not represented
  as a transcript.
- Research uses six report types and four regions (`Global`, `SEA`, `APAC`, and
  `Indonesia`), while preserving each publisher's original category and
  geography as detail metadata.
- Score mode and warnings remain visible, so an IDX market screen cannot be
  confused with a full fundamental score.
- Tools are read-only and cap result sets at 50 items.
- Every tool advertises `readOnlyHint`, `idempotentHint`, and
  `destructiveHint=false` to compatible clients.

## Install

The official MCP Python SDK requires Python 3.10 or newer. Cockpit's existing
engine can continue using its current Python; this server uses an isolated
environment.

```bash
./cockpit_mcp/setup.sh
```

On macOS, install Python first with `brew install python@3.12` if the machine
does not already have Python 3.10 or newer.

## Verify

Run the protocol smoke test:

```bash
.venv-mcp/bin/python -m cockpit_mcp.smoke_test
```

Run the MCP Inspector:

```bash
npx -y @modelcontextprotocol/inspector ./cockpit_mcp/run_mcp.sh
```

## Codex

Add the local stdio server once:

```bash
codex mcp add project-cockpit -- "$(pwd)/cockpit_mcp/run_mcp.sh"
```

Then restart Codex or open a new task. The server should appear as
`project-cockpit` and expose its tools automatically.

## Claude Code / Claude Desktop

Claude Code can read the committed project `.mcp.json`. For a standalone Claude
Desktop local configuration, start from this definition and replace the path:

```json
{
  "mcpServers": {
    "project-cockpit": {
      "command": "/ABSOLUTE/PATH/TO/Personal Website/cockpit_mcp/run_mcp.sh"
    }
  }
}
```

An example is available at
`cockpit_mcp/client-configs/claude-desktop.local.example.json`.

## Local HTTP mode

Streamable HTTP is available for local testing:

```bash
./cockpit_mcp/run_mcp.sh --transport streamable-http --host 127.0.0.1 --port 8790
```

The endpoint is `http://127.0.0.1:8790/mcp`.

With the local HTTP server running, verify it from another terminal:

```bash
.venv-mcp/bin/python -m cockpit_mcp.http_smoke_test
```

## Remote mode for Claude and ChatGPT

The included `Dockerfile` runs the same 23 tools at `/mcp`, with `/health` for
monitoring. A hosted instance reads the newest published Cockpit contracts from
`https://vitzz86.github.io`, refreshes its cache every 30 seconds, retains its
last valid payload after a temporary fetch failure, and has a bundled local
fallback snapshot.

```bash
docker build -f cockpit_mcp/Dockerfile -t project-cockpit-mcp .
docker run --rm -p 8790:8790 \
  -e COCKPIT_MCP_ALLOWED_HOSTS=localhost:8790,127.0.0.1:8790 \
  project-cockpit-mcp
```

GitHub Pages cannot run the Python MCP process. Deploy the container to a host
that provides HTTPS, then connect Claude or ChatGPT to
`https://YOUR-MCP-HOST/mcp`. Full environment, authentication, deployment, and
client instructions are in [REMOTE_SETUP.md](REMOTE_SETUP.md).

The server supports optional single-token protection through
`COCKPIT_MCP_BEARER_TOKEN`. Use it only for clients that can send a custom
Authorization header. Use OAuth for a private multi-user deployment. An
authless deployment is reasonable only when intentionally exposing Cockpit's
already-public, read-only dashboard data.

## Example questions

- `What is the current Indonesia market sentiment and what evidence supports it?`
- `Compare BBCA, BBRI, BMRI, and BBNI on score, liquidity, valuation, and risk.`
- `Why is the technology sector moving? Use related news and videos.`
- `Summarize today's Must Watch videos and distinguish title-only entries.`
- `Show recent IDX IPOs and explain which dates are confirmed.`
- `What changed in Macro Analysis, and which sources support each point?`

## Compatibility references

- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [ChatGPT developer mode and remote MCP connectors](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt-beta)
- [Claude remote custom connectors](https://support.anthropic.com/en/articles/11503834-building-custom-integrations-via-remote-mcp-servers)
