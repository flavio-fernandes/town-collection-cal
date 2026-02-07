# Architecture: Website (ARCHITECTURE_WEB.md)

## Purpose

Build a public, friendly website that helps residents quickly get a trash and recycling calendar subscription.

The backend iCalendar service already exists and is live. The website is a front-end that:
- Educates users about what an ICS subscription is (and why it is better than a one-time download).
- Lets users generate the correct ICS subscription URL for their pickup schedule.
- Helps users resolve their schedule from an address when they do not know it.
- Remains town-agnostic, so other towns can clone the repo and adapt via configuration (not code edits).

This document focuses on the website architecture, UX flows, deployment, and the exact “Codex prompt” needed to implement it cleanly.

---

## Background and constraints

### Existing backend (source of truth)

The project already provides a Flask-based service that exposes:
- `GET /town.ics` to generate ICS feeds
- `GET /resolve` to resolve an address/route without generating schedule
- `GET /version` to expose schema/DB meta
- `GET /streets` to list streets or count
- `GET /debug` to help validate what is being generated
- `GET /healthz` for health checks

The backend supports 2 usage modes for `/town.ics`:
- Mode A: Address-driven
  - `/town.ics?address=...`
  - `/town.ics?street=...&number=...`
- Mode B: Explicit bypass (no address required)
  - `/town.ics?weekday=Thursday&color=BLUE`
  - optionally `&types=trash` or `&types=trash,recycling`

Shared params:
- `days=` days ahead (default 365, capped by config)
- `types=` `trash,recycling`

The website should prefer Mode B for generated subscription URLs (privacy-friendly, no address in URL).
Use `/resolve` (and optionally `/debug`) to derive weekday/color when the user does not know them.
After resolution, generated subscription URLs must stay in Mode B and must never include address/street params.

### Website requirements

- Website files must be co-located in the same repo.
- It must be hostable by GitHub Pages from the same repo.
- Landing page must be town-agnostic and list available towns (Westford is the first and only item for now).
- Westford page must have two paths:
  1) “I know my pickup weekday and recycling bin color” -- generate ICS URL using explicit bypass.
  2) “I do not know my pickup info” -- use `/resolve` to determine weekday and color from address, including seamless handling of suggestions.
- Westford page must display backend version (from `/version`) discreetly.
- The main domain currently serving the backend must redirect (or be migrated) so that visiting the base URL shows the website.
- If website and API are on different origins, API responses must include CORS headers for browser calls.
- Selected deployment direction: **Option 1** (single public hostname with path-based edge routing).

---

## High-level architecture

### Components

1) Static website (GitHub Pages)
- A static SPA built with a stable, popular toolchain.
- Responsible for all UI, form handling, and constructing subscription links.

2) Existing backend service
- Remains the system of record for schedules.
- Provides:
  - address resolution (`/resolve`)
  - feed generation (`/town.ics`)
  - versioning (`/version`)
  - debug tools (`/debug`, `/streets`)

3) Optional edge routing layer (recommended for clean URLs)
To keep the public URLs simple (same domain for website + API), use a routing layer:
- Route `/` and all non-API paths to GitHub Pages site.
- Route `/town.ics`, `/resolve`, `/version`, `/healthz`, `/debug`, `/streets` to the backend origin.

This can be implemented via any reverse proxy or edge provider that supports path-based routing. If you prefer not to add an edge layer, use separate hostnames:
- Website: `https://trash.flaviof.com`
- API: `https://api.trash.flaviof.com`
and the website calls the API via configured base URL.

If separate hostnames are used, configure backend/proxy CORS for the website origin.

---

## URL design and routing

### Public website routes

- `/`
  - Landing page: overview + list of towns
- `/towns/<townSlug>`
  - Town page (Westford: `/towns/westford-ma`)
- `/towns/<townSlug>/about`
  - Optional: what this is, privacy, FAQ

Design goal: town pages share a generic implementation, with town-specific content and capabilities coming from config.

GitHub Pages note:
- If using React Router browser history mode, deep links like `/towns/westford-ma` need fallback handling (`404.html` redirect strategy).
- Alternatively, use hash routing to avoid deep-link 404s on Pages.

### Backend endpoints used by the site

- `GET <apiBase>/town.ics?...` (Mode B primarily)
- `GET <apiBase>/resolve?...` (address flow)
- `GET <apiBase>/version`
- Optional helper:
  - `GET <apiBase>/streets?full=true` for autocomplete

The website must never hardcode `trash.flaviof.com` in code. Use config.

---

## Configuration-first design (so other towns can clone)

### Town registry config

Add a small config file that defines towns and capabilities. Suggested path:
- `web/config/towns.yaml` (or JSON)

Example schema (conceptual):

- towns:
  - id: westford_ma
    name: "Westford, MA"
    slug: "westford-ma"
    api:
      base_url: "https://trash.flaviof.com"   # can be different in dev
      ics_path: "/town.ics"
      resolve_path: "/resolve"
      version_path: "/version"
      streets_path: "/streets"
    ui:
      hero_title: "Trash and Recycling Calendar"
      hero_subtitle: "Subscribe once, stay up to date."
      badge: "Westford"
      theme:
        gradient: "teal-to-sky"
      links:
        official_routes_doc: "https://westfordma.gov/DocumentCenter/View/2949/Trash-and-Recycling-Routes-by-Street-Name-PDF"
    capabilities:
      explicit_bypass:
        enabled: true
        weekday_values: ["Monday","Tuesday","Wednesday","Thursday","Friday"]
        color_values: ["BLUE","GREEN"]
        types_values: ["trash","recycling"]
      address_resolution:
        enabled: true
        input_fields:
          - street
          - number
        uses_suggestions: true

Future towns can set:
- explicit_bypass.enabled=false if not supported
- different input fields if their resolver requires more info

### Environment config for local dev

The website should support:
- `.env.local` for development
- `.env.production` for build-time defaults

But do not embed secrets (there should be none).

---

## UX flows

### Landing page

Content goals:
- One-paragraph explanation: “This site generates iCalendar feeds for municipal collections”.
- What you get:
  - Always up-to-date events
  - Works with Google Calendar, Apple Calendar, Outlook, Home Assistant, etc.
- Town list (cards)
  - Westford only at first
  - Each card goes to `/towns/<slug>`

### Town page (Westford)

Top section:
- Cute, inviting logo (SVG) with trash + recycling vibe.
- Clear title and short explanation.
- Subtle metadata footer pulled from `/version`:
  - `schema_version`
  - DB `generated_at` timestamp

Two main cards:
1) “I know my pickup day and bin color”
   - Inputs:
     - Weekday (dropdown, required)
     - Recycling color (dropdown, required)
     - Types (toggle buttons or checkboxes: Trash, Recycling; default both)
   - Output:
     - Primary “Subscribe” button (explains what it does)
     - Secondary “Copy URL” button
     - Shows the resulting URL:
       - `https://.../town.ics?weekday=Thursday&color=BLUE&types=trash,recycling`
   - Advanced options (collapsed by default):
     - days ahead (number input/select control with sensible min/max, default blank uses backend default)
     - types selector UI (checkboxes/toggles), default both selected
     - debug link (hidden by default, shown only when advanced troubleshooting is expanded)

2) “I do not know my pickup info”
   - Inputs:
     - Full address (single field, optional), OR
     - Street (text with autocomplete) + Number (numeric)
   - Behavior:
     - Call `/resolve?address=...` when full address is used
     - Call `/resolve?street=...&number=...` when street/number is used
     - If the backend returns a resolved match:
       - Show resolved weekday + color clearly
       - Provide the same subscribe + copy URL functionality using Mode B output
     - If the backend returns suggestions:
       - Present suggestions as a list of clickable options
       - Current backend shape is `suggestions: string[]`; clicking a suggestion should re-run resolve with same house number
     - If no match:
       - Explain next steps
       - Offer to try a different spelling
       - Provide a link to the town’s official route document (configured per town)

Important UX detail:
- Do not make users type “BLUE” and “GREEN”.
- Use dropdowns and buttons with small color indicators.
- Do not make users type `days` or `types`; use structured controls in Advanced.

### Subscription instructions

At the bottom of town page, show “How to subscribe” with tabs:
- Google Calendar
- Apple Calendar (macOS, iOS)
- Outlook
- Home Assistant

Keep the instructions short, and include:
- “Subscribe by URL” explanation
- Clarify that updates propagate automatically

Implementation detail:
- The site generates the instructions dynamically based on the selected URL.
- For Apple clients, provide a `webcal://` variant in addition to `https://`.

---

## Visual and UI guidelines (aesthetic spec)

Target vibe:
- Soft, modern, approachable.
- Glassy cards with blur.
- Theme from town config tokens (avoid hardcoding one palette).
- Subtle noise texture (optional).
- Rounded corners, gentle shadows.
- Clear section hierarchy with whitespace.
- Minimal animations (fade/slide on card entrance) that never block interaction.

Layout:
- Centered max-width container
- Card grid for sections
- Mobile-first with responsive breakpoints

Typography:
- Simple readable sans-serif
- Headings with slightly increased letter spacing
- Body text comfortable line height

Logo:
- Create a small custom SVG logo (no external dependencies).
- Must work on dark-ish gradient background.
- Town-agnostic base logo, with optional town label on town pages.

---

## Recommended web technology stack

Goal: stable, well-known, and future-proof.

Recommended stack:
- TypeScript
- React
- Vite
- Tailwind CSS
- Minimal component set (avoid heavy UI frameworks unless needed)
- Fetch via `fetch()` with a tiny wrapper for timeouts and typed responses

Testing:
- Vitest for unit tests
- Playwright for end-to-end tests (especially the address suggestion flow)

Lint/format:
- ESLint + Prettier (or Biome, but ESLint+Prettier is “most standard”)

Why:
- React + Vite is extremely common, fast to develop, easy to host as static assets, and has broad ecosystem support.

---

## Error handling and resilience

### Network failures
- Show friendly message: “Backend is temporarily unavailable”.
- Provide retry button.
- In the footer, show status from `/healthz` when available.

### Cross-origin failures (when website and API are split)
- Detect likely CORS errors and show a clear operator-facing hint in console/docs.
- Production docs must include required CORS headers and allowed origins.

### Backend schema changes
- Parse `/version` response defensively.
- The website should not require new fields to exist.

### Address ambiguity (suggestions)
- Treat suggestion handling as a first-class feature.
- Suggested UX:
  - “Did you mean...” list
  - Each option acts like a button and re-resolves cleanly
  - Keep user’s entered house number

### Privacy and logging
- The website must not store addresses.
- Do not add analytics by default.
- If you log client-side errors, do not include full addresses in logs.

---

## Local development and preview

### Local dev: web only
- `cd web`
- `npm install`
- `npm run dev`
- The API base URL comes from `.env.local`

### Local dev: web + backend via Docker (ideal)
Add a root-level `docker-compose.yml` that runs:
- backend container on `http://localhost:5000`
- web dev server on `http://localhost:5173`

Website should point to `http://localhost:5000` in this mode.

### Local production-like preview
- `npm run build`
- `npm run preview`
This ensures the generated static build behaves as GitHub Pages will.

---

## GitHub Pages deployment

Use GitHub Pages with a custom workflow:
- Build the site on push to `main`
- Upload as Pages artifact
- Deploy to the GitHub Pages environment

If using a custom domain, configure it in GitHub Pages settings and set appropriate DNS records.

Notes:
- The workflow must include the permissions required for Pages deployment.
- The repository should document how to configure the custom domain and HTTPS.
- If using SPA routes, include the Pages deep-link fallback strategy (`404.html` redirect) or hash routing.

---

## Backend domain migration plan (so base URL shows website)

Two viable options:

### Option 1 (recommended): same domain via edge routing
- Keep the public domain as the main entry point.
- Route:
  - `/` and `/towns/*` to GitHub Pages origin
  - `/town.ics`, `/resolve`, `/version`, `/healthz`, `/debug`, `/streets` to backend origin
Pros:
- Cleanest URLs
- No CORS complexity
- Existing API URLs remain valid
Cons:
- Requires an edge routing setup

### Option 2: separate domains (fallback only)
- Website: `https://trash.flaviof.com`
- API: `https://api.trash.flaviof.com`
- Requires CORS configuration on API/proxy:
  - `Access-Control-Allow-Origin: https://trash.flaviof.com`
  - Allow `GET` and required headers

Status:
- Option 1 is selected for this project.

---

## What the website must expose (features checklist)

- [ ] Town-agnostic landing page with towns list from config
- [ ] Town page generation from config
- [ ] Explicit bypass flow (weekday + color + types) producing:
  - subscribe URL
  - copy button
  - optional debug URL
- [ ] Generated subscription URLs are always Mode B (never address parameters)
- [ ] Address resolution flow using `/resolve`:
  - handles success
  - handles suggestions
  - handles no match
- [ ] Discreet backend metadata display using `/version` (`schema_version`, `generated_at`)
- [ ] Beautiful, soft, glassy UI per aesthetic spec
- [ ] CORS works for browser API calls when website/API are on different origins
- [ ] Local dev and docker-compose preview
- [ ] Tests (Vitest + Playwright)
- [ ] GitHub Actions CI:
  - lint
  - test
  - build
  - deploy to Pages

---

## Codex prompt (for implementing the website)

You are Codex working in an existing repository that already contains a Flask backend and a working production deployment of the API endpoints (`/town.ics`, `/resolve`, `/version`, etc). Your task is to add a static website into the same repo.

Goals:
1) Create a `web/` directory containing a React + TypeScript + Vite + Tailwind site.
2) The site must be town-agnostic and data-driven from `web/config/towns.yaml` (or JSON).
3) Implement these routes:
   - `/` landing page (town list)
   - `/towns/:townSlug` generic town page driven by config (Westford is configured)
4) Implement Westford page functionality (using config, not hardcoding):
   - Explicit bypass generator:
     - weekday dropdown
     - color dropdown
     - types selection (UI controls; hidden under Advanced by default)
     - days control (UI control; hidden under Advanced by default)
     - outputs final ICS URL for subscription (Mode B)
   - Address resolver:
     - input full `address` OR `street` + `number`
     - calls `/resolve` and handles:
       - resolved result -> show weekday/color and generate Mode B URL
       - suggestions -> render selectable suggestion list and re-resolve
       - no match -> friendly guidance
     - generated subscription URL after resolution must remain Mode B (no address params)
   - Footer version:
     - fetch `/version` and display schema + generated timestamp discreetly
5) Make URLs configurable:
   - Do not hardcode production hostname
   - Use `VITE_API_BASE_URL` or town config `api.base_url`
6) UI requirements:
   - Soft, modern, approachable
   - Glassy cards with blur
   - Theme colors from config tokens (no hardcoded palette)
   - Clean responsive layout
   - A small custom SVG logo with trash + recycling vibe
7) Subscription instructions section:
   - Show steps for Google Calendar, Apple Calendar, Outlook, Home Assistant
   - Generate instructions from the current selected ICS URL
   - Provide `webcal://` variant where useful
8) Add tests:
   - Unit tests for URL builder and API client (Vitest)
   - E2E tests for the two main flows (Playwright), including suggestion handling
9) Add local dev tooling:
   - `docker-compose.yml` at repo root that runs backend + web dev server
   - Clear README section: how to run locally
10) Add GitHub Actions:
   - CI workflow: lint + test
   - Pages deploy workflow: build and deploy `web/` to GitHub Pages (custom workflow)
   - Document how to set custom domain and HTTPS for Pages

Implementation notes:
- Create a tiny typed API client in `web/src/lib/api.ts` with:
  - timeout handling
  - typed responses
  - friendly error mapping
- Create a URL builder in `web/src/lib/ics.ts` that:
  - builds Mode B URLs from weekday/color/types/days
  - builds `/debug` URL optionally
  - always URL-encodes parameters correctly
  - never emits address/street params for subscription URLs
- Suggestion handling:
  - The backend currently returns `suggestions: string[]` on resolve misses.
  - Keep suggestion parsing isolated so it can be extended later if response shape evolves.
  - Keep this logic isolated and tested.

Definition of done:
- Running locally:
  - `docker compose up`
  - open the web UI and generate a working ICS URL
  - address resolution works and handles suggestions
- Production:
  - GitHub Pages publishes the site
  - API base URL is configurable
- Code quality:
  - consistent formatting, minimal dependencies
  - comprehensive docs
  - tests passing in CI
