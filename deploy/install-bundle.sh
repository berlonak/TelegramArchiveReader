#!/usr/bin/env bash
# copyright by berlonak
# telegram: @Kilax123
# Install portable pre-indexed Telegram Archive. Ubuntu/Debian VPS, no Docker.
set -euo pipefail
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
BUNDLE=/srv/tgarchive
IP="${1:-}"
EMAIL="${2:-}"
[[ "$(id -u)" == "0" ]] || die 'Запусти через sudo.' 'Use sudo.'
[[ -n "$IP" && -n "$EMAIL" ]] || die "Использование: sudo bash $BUNDLE/deploy/install-bundle.sh ПУБЛИЧНЫЙ_IPV4 EMAIL" "Usage: sudo bash $BUNDLE/deploy/install-bundle.sh PUBLIC_IPV4 EMAIL"
[[ -f "$BUNDLE/bundle-manifest.json" && -f "$BUNDLE/data/archive.sqlite3" ]] || die "Сначала положи полный готовый пакет в $BUNDLE" "Place complete bundle at $BUNDLE first"
[[ "$(realpath "$BUNDLE")" == "$BUNDLE" ]] || die 'Пакет не может быть символической ссылкой' 'Bundle cannot be a symlink'
command -v apt-get >/dev/null || die 'Скрипт рассчитан только на Ubuntu/Debian' 'Designed for Ubuntu/Debian only'
if systemctl is-active --quiet tgarchive; then
  die 'Сервис tgarchive уже работает. Останови его и сделай резервную копию базы перед переустановкой.' \
      'An existing tgarchive service is active. Stop it and back up its DB before reinstallation.'
fi
apt-get update
apt-get install -y python3 python3-venv python3-pip nginx snapd
id tgarchive >/dev/null 2>&1 || useradd --system --home /srv/tgarchive --shell /usr/sbin/nologin tgarchive
# Run validation while bundle is still at final location.
python3 "$BUNDLE/bundletool.py" verify --bundle "$BUNDLE"
python3 "$BUNDLE/bundletool.py" activate --bundle "$BUNDLE"
mkdir -p /opt/telegram-archive
cp -a "$BUNDLE/app/." /opt/telegram-archive/
chown -R root:root /opt/telegram-archive
python3 -m venv /opt/telegram-archive/.venv
/opt/telegram-archive/.venv/bin/python -m pip install --upgrade pip
/opt/telegram-archive/.venv/bin/python -m pip install /opt/telegram-archive
# Keep all original exports privately readable by the application, not by webserver users.
chown root:tgarchive "$BUNDLE"
chmod 750 "$BUNDLE"
chown -R tgarchive:tgarchive "$BUNDLE/data" "$BUNDLE/exports"
chmod 700 "$BUNDLE/data" "$BUNDLE/exports"
chmod -R go-rwx "$BUNDLE/data" "$BUNDLE/exports"
cat > /etc/systemd/system/tgarchive.service <<EOF
[Unit]
Description=Telegram Archive — private read-only Telegram history
After=network.target
[Service]
Type=simple
User=tgarchive
Group=tgarchive
WorkingDirectory=/opt/telegram-archive
Environment=TGARCHIVE_DATA_DIR=$BUNDLE/data
Environment=TGARCHIVE_HTTPS=1
Environment=TGARCHIVE_TRUST_PROXY=1
ExecStart=/opt/telegram-archive/.venv/bin/tgarchive serve --port 8000
Restart=on-failure
RestartSec=3
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$BUNDLE/data
ReadOnlyPaths=$BUNDLE/exports
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now tgarchive
systemctl is-active --quiet tgarchive || { journalctl -u tgarchive -n 40 --no-pager; exit 1; }
if ! command -v certbot >/dev/null 2>&1; then
  snap install core
  snap refresh core
  snap install --classic certbot
  ln -sfn /snap/bin/certbot /usr/local/bin/certbot
fi
bash "$BUNDLE/deploy/configure-https-ip.sh" "$IP" "$EMAIL"
# Snap typically installs its own renew timer; our additional check makes renewal explicit.
if [[ -x /snap/bin/certbot ]]; then
  cp "$BUNDLE/deploy/tgarchive-cert-renew.service" /etc/systemd/system/
  cp "$BUNDLE/deploy/tgarchive-cert-renew.timer" /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable --now tgarchive-cert-renew.timer
fi
say "Установка завершена: https://$IP" "Deployment finished: https://$IP"
say 'Важно: выполни certbot renew --dry-run; проверь вход, фото и видео.' 'Important: run certbot renew --dry-run; test login and a photo/video.'
