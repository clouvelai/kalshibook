# KalshiBook

## Kalshi API Reference

When you need Kalshi API details (endpoints, WS channels, data formats), fetch their docs index first:

- **Docs index:** `https://docs.kalshi.com/llms.txt` — 165+ pages covering REST API, WebSocket channels, SDKs
- **Individual pages:** `https://docs.kalshi.com/{path}.md` where path comes from the index

Key pages we reference often:
- WebSocket channels: `/websockets/orderbook-updates`, `/websockets/public-trades`, `/websockets/market-ticker`, `/websockets/market-&-event-lifecycle`
- Markets/Events REST: `/api-reference/market/get-market`, `/api-reference/events/get-event`, `/api-reference/events/get-event-candlesticks`
- Candlesticks: `/api-reference/market/get-market-candlesticks`, `/api-reference/market/batch-get-market-candlesticks`
- Series: `/api-reference/market/get-series`, `/api-reference/market/get-series-list`
- Trades: `/api-reference/market/get-trades`

Use `WebFetch` on `https://docs.kalshi.com/{path}` to get full endpoint details when needed.
