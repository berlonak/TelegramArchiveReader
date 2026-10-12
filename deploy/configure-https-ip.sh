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
# Messages: TGARCHIVE_LANG=ru|en, otherwise the locale (LC_ALL, LC_MESSAGES, LANG), otherwise English.
tg_lang() {
  local value="${TGARCHIVE_LANG:-}"
  value="${value,,}"
  if [[ "$value" == ru || "$value" == en ]]; then echo "$value"; return; fi
  for value in "${LC_ALL:-}" "${LC_MESSAGES:-}" "${LANG:-}"; do
    [[ -n "$value" ]] || continue
    case "${value,,}" in ru*|uk*|be*|kk*) echo ru ;; *) echo en ;; esac
    return
  done
  echo en
}
TG_LANG="$(tg_lang)"
export TGARCHIVE_LANG="$TG_LANG"
say() { if [[ "$TG_LANG" == ru ]]; then printf '%s\n' "$1"; else printf '%s\n' "$2"; fi; }
die() { say "$1" "$2" >&2; exit "${3:-2}"; }

[[ "$(id -u)" == "0" ]] || die 'Запусти через sudo.' 'Use sudo.'
[[ -n "$IP" && -n "$EMAIL" ]] || die "Использование: sudo bash $0 ПУБЛИЧНЫЙ_IP EMAIL" "Usage: sudo bash $0 PUBLIC_IP EMAIL"
python3 -c 'import ipaddress, sys; a = ipaddress.ip_address(sys.argv[1]); sys.exit(0 if a.is_global else 1)' "$IP" \
  || die "Это не публичный IP-адрес: $IP" "Not a public IP address: $IP"
command -v nginx >/dev/null || die 'nginx не установлен.' 'nginx is not installed.'
command -v certbot >/dev/null || die 'certbot не установлен.' 'certbot is not installed.'
version="$(certbot --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -n1)"
python3 -c 'import sys; v = tuple(map(int, sys.argv[1].split("."))); sys.exit(0 if v >= (5, 4) else 1)' "${version:-0.0}" \
  || die "Для IP-сертификатов через webroot нужен Certbot 5.4+ (найден: ${version:-неизвестно})." \
         "Certbot 5.4+ is required for IP certificates via webroot (found: ${version:-unknown})."

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
say "Проверяю выпуск на тестовом сервере Let's Encrypt (staging)..." "Testing issuance against the Let's Encrypt staging environment..."
certbot certonly --dry-run "${common[@]}"
say 'Запрашиваю настоящий сертификат...' 'Requesting the real certificate...'
certbot certonly --keep-until-expiring --deploy-hook 'systemctl reload nginx' "${common[@]}"
[[ -f "$LIVE/fullchain.pem" && -f "$LIVE/privkey.pem" ]] || die "Файлы сертификата не найдены в $LIVE" "Certificate files not found in $LIVE" 1

# Phase 2: enable HTTPS reverse proxy to the localhost-only application.
{ http_block; echo; https_block; } > "$SITE"
install_site
say "HTTPS настроен: https://$HOSTPART/" "HTTPS configured: https://$HOSTPART/"
