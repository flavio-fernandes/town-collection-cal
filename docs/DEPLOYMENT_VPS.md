# Deployment on a VPS (Ubuntu 22.04, Docker)

This guide covers a minimal, reliable setup to run the service in a Docker container on Ubuntu 22.04, expose it on port `8080`, and serve it publicly at:

`https://trash.flaviof.com/town.ics`

It includes:
- Docker image pull and container setup
- A `systemd` service with exponential backoff (1 minute doubling up to 15 minutes)
- Nginx reverse proxy + TLS (Let’s Encrypt)
- Required DNS records

This guide uses the prebuilt image from GitHub Container Registry (no local image build required).

All commands below are intended for your VPS (Ubuntu 22.04).


## 1) System prep

```bash
sudo apt update
sudo apt install -y git nginx ripgrep
```

Ensure the firewall and any cloud security group allow inbound `80` and `443`.


## 2) Clone repo and prepare directories

```bash
sudo mkdir -p /opt/town-collection-cal
sudo chown -R $USER:$USER /opt/town-collection-cal

git clone https://github.com/flavio-fernandes/town-collection-cal /opt/town-collection-cal
cd /opt/town-collection-cal

mkdir -p data/cache data/generated
```


## 3) Pull the Docker image from GHCR

```bash
docker pull ghcr.io/flavio-fernandes/town-collection-cal:latest
```

The published image is multi-arch (`linux/amd64` and `linux/arm64`), so it works on ARM-based VPS hosts.


## 4) Build the DB (one-time, before first run)

Run the updater inside a one-off container so you don’t need Python on the host:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e TOWN_ID=westford_ma \
  -e TOWN_CONFIG_PATH=/app/towns/westford_ma/town.yaml \
  -e OUT_PATH=/app/data/generated/westford_ma.json \
  -e CACHE_DIR=/app/data/cache \
  -v /opt/town-collection-cal/towns:/app/towns \
  -v /opt/town-collection-cal/data:/app/data \
  ghcr.io/flavio-fernandes/town-collection-cal:latest \
  python -m town_collection_cal.updater build-db \
    --town /app/towns/westford_ma/town.yaml \
    --out /app/data/generated/westford_ma.json \
    --cache-dir /app/data/cache
```

You should now have `/opt/town-collection-cal/data/generated/westford_ma.json`.
If you see a permission error, ensure `/opt/town-collection-cal/data` is writable
by your user or rerun the command with `sudo chown -R $USER:$USER /opt/town-collection-cal/data`.


## 5) Create the container (not started yet)

```bash
docker create \
  --name town-collection-cal \
  -p 8080:5000 \
  -e TOWN_ID=westford_ma \
  -e TOWN_CONFIG_PATH=/app/towns/westford_ma/town.yaml \
  -e DB_PATH=/app/data/generated/westford_ma.json \
  -v /opt/town-collection-cal/towns:/app/towns:ro \
  -v /opt/town-collection-cal/data:/app/data \
  --read-only \
  --tmpfs /tmp \
  --tmpfs /var/tmp \
  --cap-drop=ALL \
  --security-opt no-new-privileges:true \
  --pids-limit 200 \
  --memory 512m \
  --cpus 1 \
  --log-opt max-size=10m \
  --log-opt max-file=5 \
  ghcr.io/flavio-fernandes/town-collection-cal:latest
```


## 6) Exponential backoff wrapper script

Systemd on Ubuntu 22.04 doesn’t natively support exponential restart delays, so use a tiny wrapper that:
- waits `60s` after the first failure
- doubles each time
- caps at `900s` (15 minutes)
- resets to `0` after a clean exit

```bash
sudo mkdir -p /opt/town-collection-cal/bin /var/lib/town-collection-cal

cat <<'EOF' | sudo tee /opt/town-collection-cal/bin/run-container.sh >/dev/null
#!/usr/bin/env bash
set -u

STATE_FILE="/var/lib/town-collection-cal/restart_count"

count=0
if [[ -f "$STATE_FILE" ]]; then
  count="$(cat "$STATE_FILE" || echo 0)"
fi

delay=$((60 * (2 ** count)))
if (( delay > 900 )); then
  delay=900
fi

if (( delay > 0 )); then
  sleep "$delay"
fi

/usr/bin/docker start -a town-collection-cal
exit_code=$?

if [[ "$exit_code" -eq 0 ]]; then
  echo 0 > "$STATE_FILE"
else
  echo $((count + 1)) > "$STATE_FILE"
fi

exit "$exit_code"
EOF

sudo chmod +x /opt/town-collection-cal/bin/run-container.sh
```


## 7) Systemd service

```bash
cat <<'EOF' | sudo tee /etc/systemd/system/town-collection-cal.service >/dev/null
[Unit]
Description=Town Collection Cal container
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/opt/town-collection-cal/bin/run-container.sh
ExecStop=/usr/bin/docker stop town-collection-cal
Restart=on-failure
RestartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now town-collection-cal.service
```

Check status:
```bash
sudo systemctl status town-collection-cal.service
```

Verify locally:
```bash
curl -s http://127.0.0.1:8080/healthz
```


## 8) Nginx reverse proxy

Create a site config:

```bash
cat <<'EOF' | sudo tee /etc/nginx/sites-available/trash.flaviof.com >/dev/null
server {
    listen 80;
    server_name trash.flaviof.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/trash.flaviof.com /etc/nginx/sites-enabled/trash.flaviof.com
sudo nginx -t
sudo systemctl reload nginx
```


## 9) TLS certificates (Let’s Encrypt)

Install Certbot and issue a cert:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d trash.flaviof.com
```

After this, your URL should work:

```
https://trash.flaviof.com/town.ics
```

## Security hardening

**Nginx hardening**

Create a small `http`-context config for rate limiting and to hide Nginx version:

```bash
cat <<'EOF' | sudo tee /etc/nginx/conf.d/town-collection-cal-security.conf >/dev/null
server_tokens off;
limit_req_zone $binary_remote_addr zone=ics_rate:10m rate=30r/m;
limit_conn_zone $binary_remote_addr zone=addr:10m;
EOF
```

You can also copy these settings from `docs/nginx_http_context.conf`.

After Certbot has created the HTTPS server block, add these lines inside the `server { ... }` block that listens on `443` in `/etc/nginx/sites-available/trash.flaviof.com`:

```nginx
limit_req zone=ics_rate burst=20 nodelay;
limit_conn addr 20;
add_header X-Content-Type-Options nosniff always;
add_header X-Frame-Options DENY always;
add_header Referrer-Policy no-referrer always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

You can copy these server-block directives from `docs/nginx_server_security.conf`.

Then reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Docker hardening flags are already included in step 5.

## 10) DNS records

Add an `A` record for `trash.flaviof.com`:

```
Type: A
Name: trash
Value: <IP_GOES_HERE>
TTL: 300 (or your preference)
```


## Optional: Rebuild DB daily with systemd timer

Create a one-shot service that refreshes the DB:

```bash
cat <<'EOF' | sudo tee /etc/systemd/system/town-collection-cal-update.service >/dev/null
[Unit]
Description=Town Collection Cal DB updater
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/docker run --rm \
  -e TOWN_ID=westford_ma \
  -e TOWN_CONFIG_PATH=/app/towns/westford_ma/town.yaml \
  -e OUT_PATH=/app/data/generated/westford_ma.json \
  -e CACHE_DIR=/app/data/cache \
  -v /opt/town-collection-cal/towns:/app/towns \
  -v /opt/town-collection-cal/data:/app/data \
  --user 10001:10001 \
  ghcr.io/flavio-fernandes/town-collection-cal:latest \
  python -m town_collection_cal.updater build-db \
    --town /app/towns/westford_ma/town.yaml \
    --out /app/data/generated/westford_ma.json \
    --cache-dir /app/data/cache
EOF
```

Ensure the data directory is owned by the same UID the container runs as (from the Dockerfile, `10001`):

```bash
sudo chown -R 10001:10001 /opt/town-collection-cal/data
```

Create a daily timer:

```bash
cat <<'EOF' | sudo tee /etc/systemd/system/town-collection-cal-update.timer >/dev/null
[Unit]
Description=Daily Town Collection Cal DB refresh

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=10m

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now town-collection-cal-update.timer
```

Confirm schedule:
```bash
systemctl list-timers --all | rg town-collection-cal-update
```


## Troubleshooting logs (journalctl)

Scheduled DB refresh (last run):
```bash
journalctl -u town-collection-cal-update.service -n 200 --no-pager
```

Main service:
```bash
journalctl -u town-collection-cal.service -n 200 --no-pager
```

Nginx:
```bash
journalctl -u nginx -n 200 --no-pager
```

If you chose cron instead of the systemd timer, you can inspect cron logs with:
```bash
journalctl -u cron -n 200 --no-pager | rg town-collection-cal
```
