<p align="center"><img src="docs/assets/logo.svg" alt="" width="96"></p>

# bioseasy

**Encrypted iPhone and iPad backups over Wi-Fi, to your own server.** No iCloud subscription and no
cable to your computer. Backups use the same format as Finder and iTunes, so they restore with the
tools you already know.

This is a maintained fork of [werk-xyz/bioseasy](https://github.com/werk-xyz/bioseasy). It fixes
scheduled backups on TrueNAS, the setup checklist and the backup file browser, and sends alerts
through [ntfy](https://ntfy.sh). Everything needed to run it - the container image, the pairing
app for Windows, macOS and Linux, and the docs - is published here. See
[what changed](#what-is-different-in-this-fork).

> As with any backup tool you have just met: keep a second copy until you have restored from it
> yourself.

## How it works

- Runs as two containers from one image on a Linux home server or NAS: a web UI and a worker that
  runs backups and the schedule.
- You pair each iPhone or iPad **once**, over USB - at the server, or at your own computer with the
  [pairing app](#pairing-app). After that it is backed up over Wi-Fi.
- iOS asks for the passcode at the start of every backup; that is Apple's rule and no tool avoids
  it. bioseasy makes it quick: it backs up inside a time window you choose and sends an alert to
  your phone when it is time to enter the passcode, or you tap **Back up now** yourself.
- The web UI shows every device, its last good backup and whether that backup is complete. It keeps
  older generations, checks that a backup's files are really there, and lets you browse a backup
  and download single files from it without a full restore.

## Install

**A Linux host is required.** Devices are found and reached on the LAN, which needs host
networking; Docker Desktop on macOS or Windows cannot provide it.

### TrueNAS

1. Create two datasets, one for app state and one for the backups, both writable by the `apps`
   user (568).
2. **Apps -> Discover Apps -> (three dots) -> Install via YAML**, name it `bioseasy`, and paste
   [`deploy/truenas-custom-app.yaml`](deploy/truenas-custom-app.yaml) after filling in its
   placeholders.
3. Open the app's log, copy the one-time setup token, then open `https://<your NAS>:8080/setup`
   and create your admin account. The certificate is self-signed, so the browser warns once.

To see the backups from your computer, share the backup dataset over SMB like any other dataset.

### Docker Compose

```sh
git clone https://github.com/icaisolutionsb2b-hub/bioseasy.git
cd bioseasy
cp .env.example .env     # set BACKUP_ROOT, DATA_DIR, PUID/PGID
mkdir -p data backups    # or the paths you set; owned by PUID/PGID
docker compose up -d
docker compose logs bioseasy | grep "use this token"
```

Without HTTPS in front, set `BIOSEASY_SECURE_COOKIES=false` in `.env` first, or the browser drops
the session cookie and signing in fails. Then open `http://<server>:8080/setup`.

[Installation](docs/install.md) covers requirements, storage and HTTPS; every setting is in
[Configuration](docs/configuration.md). To try it with simulated devices first:
`docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d`.

## First backup

1. **Add device** in the web UI and pair the iPhone or iPad (it has to say "Trust" once).
2. Follow the setup checklist: Wi-Fi backups on, encryption on with a password you choose
   (bioseasy never stores it - without it a backup cannot be restored), then the first backup.
3. If the device is on another subnet or Bonjour cannot see it, give it a fixed IP address on your
   router and enter it under the device's **Settings -> Fixed address**.

Details: [Your first backup](docs/first-backup.md), [Pairing](docs/pairing.md),
[Restoring](docs/restore.md).

## Pairing app

A small app that pairs a phone at your own computer and sends the pairing to your server, for when
the server's USB port is out of reach. Downloads are on the
[helper-v1.0.1 release](https://github.com/icaisolutionsb2b-hub/bioseasy/releases/tag/helper-v1.0.1):

| Platform | File |
| --- | --- |
| Windows (x64) | `bioseasy-pair-windows-x64.exe` |
| macOS (Apple Silicon) | `bioseasy-pair-macos-arm64.zip` |
| Linux (x64) | `bioseasy-pair-linux-x64` |

The builds are not code-signed: Windows SmartScreen asks for **More info -> Run anyway**, and macOS
needs a right-click -> **Open** on first launch. More in [helper/README.md](helper/README.md).

## Alerts

Admin -> Notifications takes an ntfy server (`https://ntfy.sh` or your own), a topic and an
optional access token. Subscribe to the same topic in the ntfy app and you are told when a backup
succeeds or fails, when the passcode is waiting, a few minutes before a scheduled backup, when one
is overdue, and when the backup storage has a problem. On the public server anyone who knows the
topic can read it, so choose a long random one. See [Notifications](docs/notifications.md).

## What is different in this fork

- **Scheduled backups work on TrueNAS.** TrueNAS's own mDNS service holds the discovery port, so
  every scheduled check failed and no backup ever started on its own. Discovery now works around it,
  and a device with a fixed address is always checked.
- **"Only while charging"** accepts a phone that is full on the charger, and only a confirmed
  "not charging" holds a backup back.
- **The setup checklist stays finished** once a backup has succeeded, instead of coming back while
  a backup runs or after one fails.
- **The backup file browser works on real iPhone backups** and no longer redoes the slow password
  unlock on every click.
- **Alerts are ntfy only.** Email, Telegram, browser push and the Home Assistant MQTT integration
  were removed.

The full list is in the [changelog](CHANGELOG.md).

## Releases and image

- Container image: `ghcr.io/icaisolutionsb2b-hub/bioseasy` - `latest` is the newest release, a
  version tag such as `1.1.0` pins one, `edge` follows `main`. Built for `linux/amd64` and
  `linux/arm64`; pulling needs no account.
- [Releases](https://github.com/icaisolutionsb2b-hub/bioseasy/releases) carry the release notes,
  the image's software bill of materials, and the pairing app. Releases from before the fork are
  mirrored here with their original files.

## Development

```sh
uv sync
uv run ruff check src tests && uv run pytest
BIOSEASY_ENGINE=demo BIOSEASY_DATA_DIR=./data BIOSEASY_BACKUP_ROOT=./backups uv run bioseasy
```

The test suite expects Linux. Building the image and the pairing app, and cutting a release:
[Building and releasing](docs/building.md). [The docs](docs/README.md) are also shown inside the
web UI under **Guide**.

## Credits and license

Created by the authors of [werk-xyz/bioseasy](https://github.com/werk-xyz/bioseasy); this fork
keeps their history. Built on [pymobiledevice3](https://github.com/doronz88/pymobiledevice3),
[FastAPI](https://fastapi.tiangolo.com) and [htmx](https://htmx.org). Licensed under
GPL-3.0-or-later; third-party notices are in [NOTICE](NOTICE).

bioseasy is not affiliated with Apple. iPhone, iPad, iTunes and Finder are trademarks of Apple Inc.
