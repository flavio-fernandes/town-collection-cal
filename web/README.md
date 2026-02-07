# Web Frontend

Static website for generating personalized `/town.ics` subscription URLs.

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev
```

Default local URL: `http://localhost:5173`

If `VITE_DEV_PROXY_TARGET` is set (for example `http://localhost:5000`), Vite proxies API routes to the backend and the browser stays same-origin.

## Build

```bash
npm run build
npm run preview
```

## Test

```bash
npm run test
npm run test:e2e
```

## Key behavior

- Generated subscription URLs are always Mode B (`weekday`, `color`, optional `types`, optional `days`).
- Address input is only used to resolve weekday/color and is never included in the subscription URL.
- `types` and `days` are hidden under Advanced by default.
- Debug link is hidden by default.
