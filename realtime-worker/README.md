# IDX Fast Quote Gateway

This Cloudflare Worker provides Project Cockpit with a cached TradingView IDX
scanner snapshot. It does not claim exchange-licensed tick-by-tick real-time
delivery.

## Deploy

1. Authenticate Wrangler with the Cloudflare account:
   `npx wrangler login`
2. From this directory, deploy with: `npx wrangler deploy`
3. Verify: `https://<worker-domain>/health`
4. Add the Worker base URL as the GitHub repository secret
   `IDX_FAST_QUOTE_URL`.
5. Trigger `Cockpit Sync` once so the public payload receives the URL.

The dashboard then polls `/quotes?market=idx` every 60 seconds. Cloudflare caches
the upstream TradingView response for 30 seconds, so multiple dashboard visitors
do not create one upstream scanner request each.

## Data policy

- Label: `near_realtime_snapshot`
- Intended use: visible IDX prices, returns, heatmap, sector flow, and movers
- Not used to recompute fundamentals, valuation, risk ratios, or DeepSeek output
- Do not market this endpoint as an IDX-licensed real-time feed
