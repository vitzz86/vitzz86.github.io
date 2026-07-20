# Remote MCP setup

Project Cockpit supports both local `stdio` and remote Streamable HTTP. The
remote endpoint is `/mcp`; `/health` reports the payload timestamp and contract
source without exposing the payload.

## Deploy the container

Build from the repository root:

```bash
docker build -f cockpit_mcp/Dockerfile -t project-cockpit-mcp .
```

Run locally:

```bash
docker run --rm -p 8790:8790 \
  -e COCKPIT_MCP_ALLOWED_HOSTS=localhost:8790,127.0.0.1:8790 \
  project-cockpit-mcp
```

For a hosted container, set:

| Variable | Value |
|---|---|
| `COCKPIT_DATA_BASE_URL` | `https://vitzz86.github.io` |
| `COCKPIT_REMOTE_CACHE_SECONDS` | `30` |
| `COCKPIT_MCP_ALLOWED_HOSTS` | exact public hostname, without `https://` |
| `COCKPIT_MCP_ALLOWED_ORIGINS` | optional comma-separated browser origins |
| `COCKPIT_MCP_BEARER_TOKEN` | optional; only for clients that can send a bearer header |

The hosting platform must terminate HTTPS and route traffic to port `8790`.
The server fetches current `data.json`, `scores.json`, and `charts.json` from
GitHub Pages, caches them for 30 seconds, and keeps the last valid payload if a
refresh fails. The image also contains a local fallback snapshot.

## Claude

For Claude web or Claude Desktop remote connectors, add this URL in **Settings
> Connectors**:

```text
https://YOUR-MCP-HOST/mcp
```

Choose no authentication for an authless deployment. For Claude Code with a
bearer-protected endpoint:

```bash
claude mcp add --transport http project-cockpit https://YOUR-MCP-HOST/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

Local Claude Code and Claude Desktop can use `run_mcp.sh` through `.mcp.json`
or the example under `client-configs/`.

## ChatGPT

ChatGPT uses a remote HTTPS MCP endpoint rather than the local `stdio` process.
Enable developer mode, create a custom app/connector, and enter:

```text
https://YOUR-MCP-HOST/mcp
```

Choose no authentication for a public, read-only deployment. If the endpoint is
private, place it behind a supported OAuth provider or use ChatGPT's secure MCP
tunnel; a static bearer secret is intended for clients that support custom
headers and is not a replacement for multi-user OAuth.

After a deployment changes tool definitions, refresh the connector so ChatGPT
rescans the 23-tool contract.

## Codex

The local server can be registered once:

```bash
codex mcp add project-cockpit -- "$(pwd)/cockpit_mcp/run_mcp.sh"
```

For a remote deployment, configure the Streamable HTTP endpoint in the Codex
MCP settings and start a new task after changing the server definition.

## Production checklist

- Use HTTPS only.
- Keep the service read-only.
- Set the exact public hostname in `COCKPIT_MCP_ALLOWED_HOSTS`.
- Use platform rate limiting and request logs.
- Use OAuth for private multi-user deployments.
- Monitor `/health` and the `contract_health.last_fetch_errors` field.
- Run `smoke_test.py` for `stdio` and `http_smoke_test.py` for the hosted URL.
