#!/usr/bin/env bash
# copyright by berlonak
# telegram: @Kilax123
# Configure nginx + a Let's Encrypt IP-address certificate (shortlived profile) for Telegram Archive.
# Called by install-bundle.sh; can be re-run safely. Ubuntu/Debian, Certbot 5.4+ (webroot + --ip-address).
set -euo pipefail
IP="${1:-}"
EMAIL="${2:-}"
WEBROOT=/var/www/tgarchive-acme
CERT_NAME=tgarchive-ip
SITE=/etc/nginx/sites-available/tgarchive
ENABLED=/etc/nginx/sites-enabled/tgarchive
LIVE=/etc/letsencrypt/live/$CERT_NAME

[[ "$(id -u)" == "0" ]] || { echo 'Use sudo.' >&2; exit 2; }
[[ -n "$IP" && -n "$EMAIL" ]] || { echo "Usage: sudo bash $0 PUBLIC_IP EMAIL" >&2; exit 2; }
python3 -c 'import ipaddress, sys; a = ipaddress.ip_address(sys.argv[1]); sys.exit(0 if a.is_global else 1)' "$IP" \
  || { echo "Not a public IP address: $IP" >&2; exit 2; }
command -v nginx >/dev/null || { echo 'nginx is not installed.' >&2; exit 2; }
command -v certbot >/dev/null || { echo 'certbot is not installed.' >&2; exit 2; }
version="$(certbot --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -n1)"
python3 -c 'import sys; v = tuple(map(int, sys.argv[1].split("."))); sys.exit(0 if v >= (5, 4) else 1)' "${version:-0.0}" \
  || { echo "Certbot 5.4+ is required for IP certificates via webroot (found: ${version:-unknown})." >&2; exit 2; }

# IPv6 literals need brackets inside URLs.
HOSTPART="$IP"
[[ "$IP" == *:* ]] && HOSTPART="[$IP]"

mkdir -p "$WEBROOT/.well-known/acme-challenge"
chmod 755 "$WEBROOT" "$WEBROOT/.well-known" "$WEBROOT/.well-known/acme-challenge"

http_block() {
  cat <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name _;
    server_tokens off;
    location /.well-known/acme-challenge/ {
        root $WEBROOT;
    }
    location / {
        return 301 https://$HOSTPART\$request_uri;
    }
}
EOF
}

https_block() {
  cat <<EOF
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name _;
    server_tokens off;
    ssl_certificate $LIVE/fullchain.pem;
    ssl_certificate_key $LIVE/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:tgarchive:10m;
    client_max_body_size 64k;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 300s;
        # Stream large videos directly instead of spooling them to nginx temp files.
        proxy_buffering off;
    }
}
EOF
}

install_site() {
  nginx -t
  systemctl enable nginx >/dev/null
  systemctl reload nginx 2>/dev/null || systemctl restart nginx
}

# Phase 1: plain HTTP serves only the ACME challenge and redirects everything else.
http_block > "$SITE"
ln -sfn "$SITE" "$ENABLED"
# Only the stock distribution default site is disabled; any other site is left untouched.
if [[ -L /etc/nginx/sites-enabled/default && "$(readlink -f /etc/nginx/sites-enabled/default)" == /etc/nginx/sites-available/default ]]; then
  rm /etc/nginx/sites-enabled/default
fi
install_site

common=(--non-interactive --agree-tos -m "$EMAIL" --preferred-profile shortlived
        --webroot --webroot-path "$WEBROOT" --ip-address "$IP" --cert-name "$CERT_NAME")
echo 'Testing issuance against the Let'"'"'s Encrypt staging environment...'
certbot certonly --dry-run "${common[@]}"
echo 'Requesting the real certificate...'
certbot certonly --keep-until-expiring --deploy-hook 'systemctl reload nginx' "${common[@]}"
[[ -f "$LIVE/fullchain.pem" && -f "$LIVE/privkey.pem" ]] || { echo "Certificate files not found in $LIVE" >&2; exit 1; }

# Phase 2: enable HTTPS reverse proxy to the localhost-only application.
{ http_block; echo; https_block; } > "$SITE"
install_site
echo "HTTPS configured: https://$HOSTPART/"
