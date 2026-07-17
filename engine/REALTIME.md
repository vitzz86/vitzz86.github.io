# Project Cockpit Market-Data Modes

Project Cockpit separates market state from quote freshness. An exchange can be
open while the latest dashboard value is still a snapshot.

## Current production mode

- The GitHub Actions pipeline compiles the full market payload every 30 minutes.
- The browser checks for a new payload every 5 minutes without reloading the page.
- CoinGecko crypto quotes refresh in the browser every 60 seconds.
- IDX price, change, volume, market cap, and performance checkpoints come from the
  TradingView scanner. This is labelled `near_realtime_snapshot`; it is not
  represented as an exchange-licensed real-time feed.
- Market open/closed state is calculated independently from exchange session
  bounds and does not imply real-time quote delivery.

## Licensed real-time mode

True real-time IDX requires an IDX-licensed provider or redistributor. Provider
credentials must be held by a backend gateway, never in `data.json` or browser
JavaScript.

Configure these environment variables when that gateway is available:

- `IDX_FAST_QUOTE_URL`: the optional TradingView IDX snapshot gateway. The
  dashboard polls its `/quotes?market=idx` endpoint every 60 seconds.
- `REALTIME_STREAM_URL`: a public SSE endpoint that emits normalized quote events.
- `REALTIME_PROXY_URL`: a public HTTPS endpoint for normalized chart history.

The reference Cloudflare Worker for `IDX_FAST_QUOTE_URL` lives in
`realtime-worker/`. It improves visible quote freshness but remains an
unlicensed near-real-time snapshot, not tick-by-tick IDX market data.

The SSE endpoint must enable CORS for the dashboard origin and emit either one
quote or a `quotes` array:

```json
{
  "ticker": "BBCA",
  "source_symbol": "BBCA.JK",
  "country": "ID",
  "price": 9250,
  "change_percent": 0.82,
  "asof": 1784282400,
  "source": "licensed IDX feed"
}
```

The chart endpoint contract is:

`GET {REALTIME_PROXY_URL}/chart?symbol=BBCA.JK&country=ID&range=6mo`

```json
{
  "value": 9250,
  "delta_pct": 0.82,
  "quote_asof": 1784282400,
  "intraday": [9180, 9200, 9250],
  "spark": [8700, 8825, 9100, 9250],
  "spark_ts": [1768435200, 1771113600, 1773792000, 1784246400]
}
```

The gateway should enforce rate limits, cache provider responses, validate symbol
entitlements, and expose no provider API key to the client.

## Security rule

`FINNHUB_API_KEY`, YouTube keys, DeepSeek keys, and all other provider credentials
are backend-only secrets. Rotate any key that has previously appeared in a public
payload or Git history.
