# Notifications

This page is for whoever administers this bioseasy install and wants to be told when something
needs attention.

bioseasy sends every alert through [ntfy](https://ntfy.sh): a backup that succeeded or failed, a
passcode waiting to be entered on the device, the notice a few minutes before a scheduled backup,
a backup that is due or overdue, and a backup volume that is low on space or not mounted.

## Setting it up

1. Install the ntfy app on your phone (App Store, Google Play or F-Droid).
2. In bioseasy, open **Admin -> Notifications** and fill in:
   - **Server**: `https://ntfy.sh`, or the address of your own ntfy server.
   - **Topic**: any name made of letters, digits, `-` and `_`. On the public ntfy.sh server anyone
     who knows a topic can read it, so use something long and unguessable
     (for example `bioseasy-7f3k9q2m8x`).
   - **Access token** (optional): for a server or topic that requires one. It is stored encrypted
     and never shown again; leave the field blank to keep the stored token.
3. Tick **Send alerts**, save, and press **Send test message**.
4. In the ntfy app, subscribe to the same topic (and the same server, if it is your own).

Set `BIOSEASY_BASE_URL` (see [Configuration](configuration.md)) and tapping an alert opens that
device's page in bioseasy.

Every device's alerts go to this one topic; the title names the device. Failures, overdue backups
and a waiting passcode are sent at high priority, a storage problem at the highest.

## Secrets at rest

The ntfy access token is encrypted with a key kept in
`<data dir>/connector.key`, apart from the database file. This protects a copied database file,
not someone who can already read the whole data volume.
