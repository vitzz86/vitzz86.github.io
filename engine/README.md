# Project Cockpit — engine

Autonomous data-generation architecture behind [`/cockpit.html`](../cockpit.html).
Agents run sequentially as a LangGraph state machine and compile three strict
static contracts: `data.json` for the primary dashboard, `scores.json` for
lazy-loaded score detail, and `charts.json` for lazy-loaded chart history. A
Cloudflare Worker supplies the 60-second TradingView IDX snapshot; the static
payload remains the fallback when that gateway or an upstream provider fails.

```
[Quant] → Δ>1.2% check → [OSINT Hunter (Tavily override on anomaly)]
       → [Cross-Market Arbiter] → [Chief of Staff → data.json + scores.json]
```

## v2 — Sector Flow Matrix & universal link layer

`data.json` also carries the v2 cockpit surfaces, baked at cron time so the
dashboard has a stable payload even when optional live overlays fail:

- **`sectors`** — 11-sector-style equity universe (`config/settings.py → SECTORS`,
  extensible with no code changes). `tools/sectors.py` fetches each constituent's
  day delta + 6-month sparkline via TradingView IDX, Yahoo, and CoinGecko, computes regional
  aggregates, a Mega/Large/Mid/Small tier, an ALERT/WATCH/NORMAL signal, and a
  synthesis line. Falls back to flat 0.0 when providers are unreachable, so the
  grid always renders.
- **`universe`** — shared registry layer for active Sector Flow rows and
  price-only global leaders. It owns country/region tags, source URLs, data
  tiers, refresh-frequency labels, and coverage summaries so heatmap, movers,
  scoring, and future universe expansion do not fork separate schemas.
- **IDX classification** — TradingView's specific industry is mapped before its
  broad sector, preventing agriculture, textiles, packaging, insurers, and
  property developers from leaking into unrelated Cockpit sectors. Mixed
  businesses use an explicit ticker override with a named industry; source
  health reports exact-industry, override, and fallback counts each run.
- **`news`** — `tools/news_router.py` accumulates seven days of deduplicated
  Google News/trusted-source discovery. A persisted attempt ledger rotates a
  bounded query budget through top-120 Indonesia, top-120 US, top-100 crypto,
  and monitored leaders in every other country. Sector items must pass a
  ticker-or-sector relevance gate and every displayed item has a source URL.
- **`ipo`** — `tools/ipos.py` keeps recent one-year IDX/US listings, confirmed schedules,
  filed/reported pipeline candidates, official e-IPO prospectus links and KSEI registration
  documents when available, plus official S&P 500 membership announcements. Filing and
  publication dates are never presented as listing dates. IDX recent dates use
  TradingView's first observed bar as a clearly labelled proxy;
  US IPO industries are joined from Nasdaq's active-stock screener and official
  SEC filing searches are linked without inventing classifications. S&P additions
  are never described as IPOs. Previous schedules survive source maintenance and
  temporary network failures. Each IPO view includes one Indonesia and one US/global
  synthesis sentence grounded in the displayed counts, names, and industries. The
  DeepSeek result is cached by an IPO-data signature and falls back to the same
  source-grounded deterministic facts when the model is unavailable.
- **Scoring guardrails** — deterministic ticker scoring never uses DeepSeek.
  Fair value is hidden when an equity lacks an observed current/forward P/E
  (banks use the separate P/B model), and Sharpe/Sortino/drawdown are calculated
  only from genuine historical closes, never TradingView checkpoints.

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
python engine/cockpit_worker.py        # writes data.json + scores.json + charts.json atomically
PYTHONPATH=engine python -m unittest discover -s engine/tests -v
```

## Deploy

`.github/workflows/cockpit_sync.yml` is triggered by cron-job.org via
`workflow_dispatch` and commits `data.json`, `scores.json`, and `charts.json` back to the repo.
Add the env vars above as repository **Secrets**. Failures leave the previous
published payload untouched.
