# nginx deployment and recovery

This document describes the production reverse-proxy layout used for `trash.flaviof.com`, including an important boot-time reliability rule discovered after an Oracle Cloud VM reboot.

## Production layout

The expected production path is:

1. The `town-collection-cal` container serves the Flask API on host port `8080`.
2. nginx terminates TLS on ports `80` and `443`.
3. API paths are proxied to `http://127.0.0.1:8080`.
4. Website paths are redirected to the GitHub Pages frontend.

The API and website are intentionally handled differently:

- API requests must be proxied to Flask.
- Website requests should be redirected to GitHub Pages.

## Important boot-time DNS failure mode

Do not proxy the GitHub Pages website through nginx using a static external hostname:

```nginx
location ^~ /town-collection-cal/ {
    proxy_pass https://flavio-fernandes.github.io;
}
```

With this form of `proxy_pass`, nginx resolves the upstream hostname while validating or starting its configuration. If DNS is not ready during boot, nginx can fail with:

```text
nginx: [emerg] host not found in upstream "flavio-fernandes.github.io"
```

The failure is fatal. nginx does not start, so nothing listens on ports `80` or `443`, even when the application container remains healthy on port `8080`.

This can produce an external symptom such as:

```text
connect to trash.flaviof.com port 443 failed: Connection refused
```

The safer design is to return an HTTP redirect. nginx does not need to resolve the destination hostname for a `return` directive. The client performs that DNS lookup after receiving the redirect.

## Recommended site configuration

The following configuration preserves the public API endpoints and redirects browser traffic to GitHub Pages:

```nginx
server {
    server_name trash.flaviof.com;

    # Flask API endpoints.
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

    # Preserve URLs that already contain the GitHub Pages project prefix.
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

Use `302` redirects while testing. After the routing has been stable and verified, permanent `301` or `308` redirects may be used where appropriate.

## Safe configuration update procedure

Resolve the enabled site to its real file, make a timestamped backup, edit the file, validate nginx, and only then restart it.

```bash
set -euo pipefail

NGINX_LINK=/etc/nginx/sites-enabled/trash.flaviof.com
NGINX_SITE=$(readlink -f "${NGINX_LINK}")
BACKUP=${NGINX_SITE}.$(date +%Y%m%d-%H%M%S).bak

printf 'Editing: %s\n' "${NGINX_SITE}"
printf 'Backup:  %s\n' "${BACKUP}"

sudo cp -a "${NGINX_SITE}" "${BACKUP}"
sudo nginx -t
```

After making the edit:

```bash
set -euo pipefail

sudo nginx -t
sudo systemctl restart nginx
sudo systemctl --no-pager --full status nginx | sed -n '1,40p'
```

Never restart nginx after a failed `nginx -t`.

## Verification

### Confirm listeners

```bash
sudo ss -lntp |
    awk 'NR == 1 || $4 ~ /:(80|443|8080)$/'
```

Expected:

- nginx listens on ports `80` and `443`.
- Docker publishes the application on port `8080`.

### Confirm the backend directly

```bash
curl -fsS http://127.0.0.1:8080/healthz
echo
```

### Test nginx locally with production TLS and SNI

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

Expected:

- `/` returns a redirect to the GitHub Pages website.
- `/healthz` returns a successful JSON response.
- `/town.ics` begins with `BEGIN:VCALENDAR`.

### Test from another system

```bash
curl -sSIL https://trash.flaviof.com/
curl -fsS https://trash.flaviof.com/healthz
echo

curl -fsS \
    "https://trash.flaviof.com/town.ics?weekday=Thursday&color=BLUE" |
    sed -n '1,15p'
```

## Troubleshooting `Connection refused`

A refused TCP connection means the problem occurs before TLS or HTTP processing. DNS can be correct while nginx is not running.

Check in this order:

```bash
set -o pipefail

sudo ss -lntp |
    awk 'NR == 1 || $4 ~ /:(80|443|8080)$/'

sudo systemctl --no-pager --full status nginx
sudo nginx -t
sudo journalctl -u nginx -b --no-pager -n 200

sudo docker ps -a \
    --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}'
```

Interpretation:

- Port `8080` is listening but `443` is not: nginx is down or failed validation.
- nginx reports `host not found in upstream`: remove the external website `proxy_pass` and use an HTTP redirect.
- nginx is listening but public traffic times out: inspect host firewall and Oracle Cloud ingress rules.
- TCP connects but TLS fails: inspect the certificate, private key, SNI, and Certbot configuration.
- TLS succeeds but a path returns an HTTP error: inspect nginx path routing and Flask routes.

## Tailscale DNS note

A local `dig` command may show the resolver as:

```text
SERVER: 100.100.100.100#53
```

That address is Tailscale's local DNS forwarder. It can resolve ordinary public DNS names and does not imply that the returned service address is inside the tailnet.

For example, if the answer is the public address `193.122.136.53`, HTTPS traffic is still sent to that public address. To compare against public resolvers directly:

```bash
dig @1.1.1.1 +short trash.flaviof.com A
dig @8.8.8.8 +short trash.flaviof.com A
```

## Reboot validation

This failure was exposed by a reboot, so production validation should include one controlled reboot after nginx configuration changes:

```bash
sudo reboot
```

After reconnecting:

```bash
sudo systemctl --no-pager --full status nginx
sudo ss -lntp |
    awk 'NR == 1 || $4 ~ /:(80|443|8080)$/'

curl -fsS https://trash.flaviof.com/healthz
echo
```

The important invariant is that nginx must be able to validate and start without depending on DNS resolution of the external GitHub Pages hostname.