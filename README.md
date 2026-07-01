# Town Collection Cal

Town-agnostic service that publishes an iCalendar (ICS) feed for trash and recycling pickup dates.

It uses a two-phase design:
1. **Updater**: downloads town source documents, parses them, applies YAML overrides, and writes a validated JSON database.
2. **Service**: loads the JSON database and serves ICS + debug endpoints.

## Quick Start (Local)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Optional address parsing (recommended):
```bash
pip install -e ".[dev,address]"
```

Notes:
- On Python 3.14, the `usaddress` extra is skipped because `python-crfsuite` does not provide wheels and often fails to build.
- If you need `usaddress` parsing on macOS, install Xcode CLI tools: `xcode-select --install`, then use Python 3.13 or install `usaddress` manually.

Build the DB:
```bash
python -m town_collection_cal.updater build-db \
  --town towns/westford_ma/town.yaml \
  --out data/generated/westford_ma.json \
  --cache-dir data/cache
```

Run the service:
```bash
export TOWN_ID=westford_ma
export TOWN_CONFIG_PATH=$(pwd)/towns/westford_ma/town.yaml
export DB_PATH=$(pwd)/data/generated/westford_ma.json
export FLASK_APP=town_collection_cal.service.app:create_app
python -m flask run --host 0.0.0.0 --port 5000
```

## Docker
Development image (includes optional address parsing):
```bash
docker build -f Dockerfile.dev -t town-collection-cal:dev .
docker run --rm -p 5000:5000 \
  -e TOWN_ID=westford_ma \
  -e TOWN_CONFIG_PATH=/app/towns/westford_ma/town.yaml \
  -e DB_PATH=/app/data/generated/westford_ma.json \
  -v "$PWD/towns:/app/towns" \
  -v "$PWD/data:/app/data" \
  town-collection-cal:dev
```

Production image (includes optional address parsing):
```bash
docker build -t town-collection-cal:prod .
docker run --rm -p 5000:5000 \
  -e TOWN_ID=westford_ma \
  -e TOWN_CONFIG_PATH=/app/towns/westford_ma/town.yaml \
  -e DB_PATH=/app/data/generated/westford_ma.json \
  -v "$PWD/towns:/app/towns" \
  -v "$PWD/data:/app/data" \
  town-collection-cal:prod
```

## Production Reverse Proxy (nginx)

A typical production layout is:

- The Flask container listens on `127.0.0.1:8080` or another non-public application port.
- nginx terminates TLS on ports 80 and 443.
- API paths are proxied to Flask.
- Website paths are redirected to the GitHub Pages frontend.

### Important boot-time reliability rule

Do not proxy the GitHub Pages website through nginx with a static hostname such as:

```nginx
location ^~ /town-collection-cal/ {
    proxy_pass https://flavio-fernandes.github.io;
}
```

nginx resolves a hostname used by this form of `proxy_pass` while validating or starting its configuration. If DNS is not ready during boot, nginx can fail completely with an error similar to:

```text
nginx: [emerg] host not found in upstream "flavio-fernandes.github.io"
```

When this happens, nothing listens on ports 80 or 443, even if the application container remains healthy.

For website navigation, use HTTP redirects instead. Redirects do not require nginx to resolve the destination hostname. The browser resolves the GitHub Pages hostname after receiving the redirect.

### Recommended nginx configuration

This example keeps the API at `trash.flaviof.com` and redirects website traffic to GitHub Pages:

```nginx
server {
    server_name trash.flaviof.com;

    # Application API endpoints.
    location ~ ^/(town\.ics|resolve|version|healthz|debug|streets)$ {
        proxy_pass http://127.0.0.1:8080;

        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Main website entry point.
    location = / {
        return 302 https://flavio-fernandes.github.io/town-collection-cal/;
    }

    # Preserve links that already include the GitHub Pages project prefix.
    location ^~ /town-collection-cal/ {
        return 302 https://flavio-fernandes.github.io$request_uri;
    }

    # Redirect other non-API paths into the GitHub Pages project.
    location / {
        return 302 https://flavio-fernandes.github.io/town-collection-cal$request_uri;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/trash.flaviof.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/trash.flaviof.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

    limit_req zone=ics_rate burst=20 nodelay;
    limit_conn addr 20;

    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy no-referrer always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}

server {
    if ($host = trash.flaviof.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name trash.flaviof.com;
    return 404; # managed by Certbot
}
```

Use `302` while testing. After the routing has been stable and verified, changing permanent redirects to `301` or `308` is optional.

### Safe update procedure

Always back up and validate the nginx configuration before restarting:

```bash
set -euo pipefail

NGINX_SITE=$(readlink -f /etc/nginx/sites-enabled/trash.flaviof.com)
BACKUP=${NGINX_SITE}.$(date +%Y%m%d-%H%M%S).bak

sudo cp -a "${NGINX_SITE}" "${BACKUP}"
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl --no-pager --full status nginx
```

If the configuration was edited after the backup, run `sudo nginx -t` again immediately before restarting.

### Verification

Confirm that nginx and the application port are listening:

```bash
sudo ss -lntp |
  awk 'NR == 1 || $4 ~ /:(80|443|8080)$/'
```

Test the backend directly:

```bash
curl -fsS http://127.0.0.1:8080/healthz
echo
```

Test nginx locally while preserving the production hostname and TLS SNI:

```bash
curl -sSIk \
  --resolve trash.flaviof.com:443:127.0.0.1 \
  https://trash.flaviof.com/

curl -fsSk \
  --resolve trash.flaviof.com:443:127.0.0.1 \
  https://trash.flaviof.com/healthz
echo

curl -fsSk \
  --resolve trash.flaviof.com:443:127.0.0.1 \
  "https://trash.flaviof.com/town.ics?weekday=Thursday&color=BLUE" |
  sed -n '1,15p'
```

Expected results:

- `/` returns a redirect to the GitHub Pages website.
- `/healthz` returns a successful JSON response.
- `/town.ics` begins with `BEGIN:VCALENDAR`.

Test publicly from another system:

```bash
curl -sSIL https://trash.flaviof.com/
curl -fsS https://trash.flaviof.com/healthz
echo
```

### Troubleshooting connection refused

If clients report:

```text
Failed to connect to trash.flaviof.com port 443: Connection refused
```

check these in order:

```bash
sudo ss -lntp |
  awk 'NR == 1 || $4 ~ /:(80|443|8080)$/'

sudo systemctl --no-pager --full status nginx
sudo nginx -t
sudo journalctl -u nginx -b --no-pager -n 200
sudo docker ps -a \
  --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}'
```

Interpretation:

- Application on 8080, but nothing on 443: nginx is down or failed validation.
- nginx reports `host not found in upstream`: remove the external website `proxy_pass` and use a redirect.
- nginx is listening, but public traffic times out: inspect the host firewall and cloud ingress rules.
- TLS errors occur only after TCP connects: inspect the certificate and SNI configuration.

## Website (Frontend)
The repository now includes a static web app in `web/` that helps residents generate subscription URLs without exposing addresses in the final URL.

Quick start:
```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

Recommended full local stack:
```bash
docker compose up --build
```

Then open:
- Web UI: `http://localhost:5173`
- Backend API is reachable through the web dev server proxy on the same origin (`http://localhost:5173`).

Port-conflict options:
- Change web host port:
  - `HOST_WEB_PORT=5180 docker compose up --build`
- Expose backend directly on host only when needed:
  - `docker compose -f docker-compose.yml -f docker-compose.backend-host.yml up --build`
- Change direct backend host port:
  - `HOST_BACKEND_PORT=5001 docker compose -f docker-compose.yml -f docker-compose.backend-host.yml up --build`

## Endpoints
- `GET /healthz` -> `{ ok: true }`
- `GET /version` -> service version + DB meta + schema version
- `GET /streets` -> count of streets (use `?full=true` for list)
- `GET /debug` -> resolved route + next pickup dates + preview list
- `GET /town.ics` -> ICS feed
- `GET /resolve` -> resolve address/route without generating schedule

## `/town.ics` usage

### Mode A: Address-driven
```text
/town.ics?address=65%20Boston%20Road,%20Westford,%20MA%2001886
/town.ics?street=Boston%20Road&number=65
```

Resolve-only:
```text
/resolve?street=Boston%20Road&number=65
```

### Mode B: Explicit bypass (no address required)
```text
/town.ics?weekday=Thursday&color=BLUE
/town.ics?weekday=Thursday&color=BLUE&types=trash
```

Website behavior note:
- the UI always emits Mode B subscription URLs (privacy-friendly).
- address inputs are only used for route resolution and preview.

### Shared params
- `days=` number of days ahead (default 365, capped by config)
- `types=` comma list: `trash,recycling`

## Adding a New Town
1. Create `towns/<town_id>/town.yaml`.
2. Provide source URLs and parser plugin paths.
3. Add overrides:
   - `street_aliases.yaml`
   - `route_overrides.yaml`
   - `holiday_rules.yaml`
4. Run the updater, then start the service.

## Overrides Format
`route_overrides.yaml` supports:
```yaml
add:
  - street: "Example Street"
    weekday: "Thursday"
    recycling_color: "BLUE"
    parity: "odd"
    range: [1, 99]
delete:
  - street: "Example Street"
    weekday: "Thursday"
patch:
  - street: "Example Street"
    weekday: "Thursday"
    recycling_color: "GREEN"
```

`holiday_rules.yaml` supports:
```yaml
no_collection_dates:
  - "2025-07-04"
shift_holidays:
  - "2025-07-04"
  - "2025-09-01"
  - "2025-12-25"
```

## Development
```bash
ruff check .
pytest
```

Unified workflow via `make` (recommended):
```bash
make bootstrap-py
make bootstrap-web
make check
```

Other useful targets:
- `make test-py`
- `make test-web`
- `make build-web`
- `make audit-py`
- `make audit-web`
- `make help`

## Sanity Check
```bash
make sanity
```

## Postman
Import `postman/town-collection-cal.postman_collection.json`.

## Parsing and Troubleshooting
See `docs/PARSING.md`.

## Home Assistant
Add the ICS URL as a calendar source:
```
https://<host>/town.ics?address=65%20Boston%20Road,%20Westford,%20MA%2001886
```
