# Project Cockpit — engine

Autonomous data-generation architecture behind [`/cockpit.html`](../cockpit.html).
Four agents run sequentially as a LangGraph state machine and compile the strict
`data.json` contract the dashboard reads client-side (no runtime API calls).

```
[Quant] → Δ>1.2% check → [OSINT Hunter (Tavily override on anomaly)]
       → [Cross-Market Arbiter] → [Chief of Staff → data.json]
```

## v2 — Sector Flow Matrix & universal link layer

`data.json` also carries two v2 surfaces, baked at cron time so the static
dashboard needs no live backend:

- **`sectors`** — 10-sector-style equity universe (`config/settings.py → SECTORS`,
  extensible with no code changes). `tools/sectors.py` fetches each constituent's
  day delta + 20-pt sparkline via yfinance, computes ID-vs-US aggregates, a
  Mega/Large/Mid/Small tier, an ALERT/WATCH/NORMAL signal, and a synthesis line.
  Falls back to flat 0.0 when yfinance is unreachable, so the grid always renders.
- **`news`** — `tools/news_router.py` turns RSS headlines into a deduped list
  where **every item has a verified source URL** (items without a link are
  suppressed, per PRD D3), tagged with a category and routed to sectors.

The cockpit renders the sector grid + per-sector modal (constituents, sparklines,
themes, synthesis, routed news) entirely client-side from this baked payload.

## LLM intelligence base — DeepSeek

Set **one** of these (checked in this order):

| Env var | Route | Model |
|---|---|---|
| `DEEPSEEK_API_KEY` | api.deepseek.com (native) | `deepseek-chat` (override: `COCKPIT_MODEL_NATIVE`) |
| `OPENROUTER_API_KEY` | OpenRouter free tier | `deepseek/deepseek-v4-flash` (override: `COCKPIT_MODEL`) |

With no key configured the pipeline still completes through deterministic
fallbacks (telemetry + raw headlines), so the dashboard never breaks.

## Optional integrations ($0 tier)

- `TAVILY_API_KEY` — deep web hunt, fired only on a Market Anomaly Event.
- `GCAL_ICS_URL` — secret iCal address of your Google Calendar → focus pill.
- `COCKPIT_NOTE_URL` — raw-text URL (e.g. GitHub Gist raw) for Note of the Day.

## Run locally

```bash
pip install -r engine/requirements.txt
python engine/cockpit_worker.py        # writes ../data.json atomically
```

## Deploy

`.github/workflows/cockpit_sync.yml` runs the pipeline at 06:00 & 18:00 WIB via
GitHub Actions and commits `data.json` back to the repo. Add the env vars above
as repository **Secrets**. Failures leave the previous `data.json` untouched.
