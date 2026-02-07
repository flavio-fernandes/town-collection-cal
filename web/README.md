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

## Enable GitHub Pages

This repo deploys Pages via `.github/workflows/web-pages.yml`.

1. In GitHub, open `Settings` -> `Pages`.
2. Under `Build and deployment`, set `Source` to `GitHub Actions`.
3. Push to `main` (or run `Web Pages Deploy` workflow manually).
4. Confirm the workflow succeeds and note the published URL from the `deploy` job.

Recommended checks:
- `Settings` -> `Actions` -> `General` allows Actions to run for this repo.
- If using a custom domain for direct Pages access, configure it in `Settings` -> `Pages`.

For Option 1 routing in this project, Nginx proxies `/` to the default Pages origin, so a custom Pages domain is optional.

## Key behavior

- Generated subscription URLs are always Mode B (`weekday`, `color`, optional `types`, optional `days`).
- Address input is only used to resolve weekday/color and is never included in the subscription URL.
- `types` and `days` are hidden under Advanced by default.
- Debug link is hidden by default.
