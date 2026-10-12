# Deploying the ready bundle to a server without Docker

The recommended path is to **build and index the archive on Windows**, then transfer the **ready folder** to the server. It is a **portable directory**, not a Docker container and not a Windows `.exe`: Linux only installs the server-side Python dependencies. **The export is not re-indexed on the server.**

**Requirements:** a dedicated VPS with Ubuntu 22.04/24.04 or Debian 12/13, `sudo` and SSH, a **static public IPv4 address**, open TCP ports **80/443**, and enough SSD space for the source folder + SQLite + headroom (roughly three times the export size if nothing else runs there). The automatic script is designed for a **clean server**; if sites, nginx or certbot are already running, check for conflicts and align their configuration manually. The private export is stored on the server disk **without end-to-end encryption**.

**Message language.** The scripts use Russian when the server or SSH session locale is Russian (`LANG=ru_RU.UTF-8`) and English otherwise. To choose explicitly: `sudo TGARCHIVE_LANG=en bash ...` (or `ru`). Русская версия: [SERVER-RU.md](SERVER-RU.md).

## 1. Transfer the folder via WinSCP/SFTP

On Windows **stop the local `START-LOCAL.bat` (`Ctrl+C`)** and wait until it exits. Do not copy an active SQLite database with an unfinished WAL. Use WinSCP to upload the **contents** of `TelegramArchive-ready` to `~/tgarchive-upload/` on the server, including `app`, `data`, `exports`, `deploy`, `bundletool.py` and `bundle-manifest.json`. For a large export a folder over SFTP is more convenient than a TAR: missing files can be resumed after a failure.

Over SSH on the server:

```bash
mkdir -p ~/tgarchive-upload
# After the upload has finished, from SSH:
python3 ~/tgarchive-upload/bundletool.py verify --bundle ~/tgarchive-upload --full
```

The command checks the SHA256 of the JSON, the number and total size of the source files, and that the media exist. **It does not compute the SHA256 of each of tens of thousands of media files.** For maximum assurance of the transfer, also keep a manifest with file hashes and an independent backup.

## 2. Install the web application (no Docker)

The steps below assume that `/srv/tgarchive` does **not exist yet**. First make sure there is no old archive or someone else's data there.

```bash
test ! -e /srv/tgarchive || { echo 'Already exists: review it first'; exit 1; }
sudo mv "$HOME/tgarchive-upload" /srv/tgarchive
sudo python3 /srv/tgarchive/bundletool.py verify --bundle /srv/tgarchive --full
sudo bash /srv/tgarchive/deploy/install-bundle.sh PUBLIC_IP YOUR_EMAIL
```

Replace `PUBLIC_IP` with your IPv4 address and `YOUR_EMAIL` with the address for certificate notices. **Run the installer only after the full transfer and verification.** It installs Python, a systemd service, nginx, Certbot 5.4+ and sets up HTTPS for the **IP address**. `tgarchive` listens **only on `127.0.0.1:8000`**; do NOT open that port to the outside.

**Let's Encrypt IP-address certificates are available now**, but they are short-lived (about six days), so the script creates a regular renewal timer and an nginx reload hook, and first tests issuance on the staging environment. The server must be reachable on port 80 for IP ownership validation. If issuance fails, **do not enter the password over HTTP**: fix port 80 access, the Certbot version and the HTTPS setup, then rerun the configuration after reading the error message.

## 3. Check before use

```bash
sudo systemctl status tgarchive nginx tgarchive-cert-renew.timer --no-pager
sudo nginx -t
sudo certbot certificates
sudo certbot renew --dry-run
sudo ss -lntp | grep -E ':80|:443|:8000'
```

Then open **`https://PUBLIC_IP/`** on a computer and a phone. Check sign-in, search, scrolling **in both directions**, loading photos and a few videos. On the external interface **only** nginx on 80/443 (and SSH on your chosen port) should answer; the app on 8000 is localhost only.

If something does not work:

```bash
sudo journalctl -u tgarchive -n 80 --no-pager
sudo systemctl status nginx --no-pager
sudo certbot renew --dry-run
```

## Alternative: one TAR

Transfer `tgarchive.tar` over SFTP (you need space for both the TAR and the unpacked set). On the server:

```bash
sudo mkdir /srv/tgarchive
sudo tar -xf ~/tgarchive.tar -C /srv/tgarchive --strip-components=1
sudo python3 /srv/tgarchive/bundletool.py verify --bundle /srv/tgarchive --full
sudo bash /srv/tgarchive/deploy/install-bundle.sh PUBLIC_IP YOUR_EMAIL
```

**Never unpack a TAR from an untrusted source as root**; this file must be your own build, transferred over SSH.

## What if you really want a Docker container?

**Do not** bake gigabytes of conversations into a Docker image. The project has `deploy/docker/compose.yaml`: the image is built on the server from `TelegramArchive-ready/app/` only, and the export and SQLite are mounted separately. Put a copy of `compose.yaml` **next to** the `TelegramArchive-ready` folder on Linux and fix the permissions of `data/` and `exports/` for UID 10001 before starting. Docker listens **only on `127.0.0.1:8000`**; nginx and HTTPS are still configured on the host. **Do NOT run systemd and Docker on port 8000 at the same time.** For a single private archive the no-Docker setup above is recommended: it is shorter and already matches the portable bundle.

## Security

- The password (Argon2id) and HTTPS protect web access; they **do not encrypt the disk**. Keep separate **encrypted** backups.
- Do not serve the contents of `exports/` and `data/` directly through nginx: access to photos and JSON is controlled by FastAPI.
- Use SSH keys and a firewall. Do not publish `bundle-manifest.json`, especially together with private data, in a public repository.
- Automated tests and these instructions do not replace an independent audit of a public web application; for a really sensitive full archive, private VPN access (for example Tailscale) is safer than direct publication by IP.
