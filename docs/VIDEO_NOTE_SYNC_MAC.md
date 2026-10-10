# Video notes: periodic server-to-Mac sync

The Mac owns the Obsidian vault. Vasya can queue a reviewed transcript on the
server while the Mac is offline. This LaunchAgent checks the queue every five
minutes, writes notes under `30_Knowledge/Video`, and acknowledges a revision
only after the file is written. Repeated runs update the same note.

## Prerequisites

- Run these commands from the Vasya checkout that will remain on this Mac,
  using its installed Python environment.
- The server has `VASYA_VIDEO_NOTE_QUEUE_MODE=true` and a configured
  `VASYA_API_AUTH_TOKEN`. Its API is reachable over HTTPS or a localhost tunnel.
- The vault exists on this Mac. Do not mount or copy the private vault into the
  server's repository.
- Save the server API token in an owner-only regular file outside Git, such as
  `~/Library/Application Support/Vasya/video-note-sync.key`. Set its permissions
  to `0600`. Do not put the token in the LaunchAgent plist or command line.

## Verify once, then schedule

Replace the example URL and vault path with the actual values. The key file
must already contain the server API token.

```bash
KEY_FILE="$HOME/Library/Application Support/Vasya/video-note-sync.key"
VAULT="$HOME/Documents/Obsidian Vault"
SERVER="https://vasya.example.invalid"

chmod 600 "$KEY_FILE"
.venv/bin/python -m scripts.sync_video_notes \
  --server "$SERVER" --vault "$VAULT" --api-key-file "$KEY_FILE"

.venv/bin/python -m scripts.video_note_sync_launchd render \
  --server "$SERVER" --vault "$VAULT" --api-key-file "$KEY_FILE"

.venv/bin/python -m scripts.video_note_sync_launchd install \
  --server "$SERVER" --vault "$VAULT" --api-key-file "$KEY_FILE"
```

`render` prints the plist without installing it or contacting the server. The
installer refuses to overwrite an existing agent, verifies the key file, and
loads `~/Library/LaunchAgents/com.vasya.video-note-sync.plist`. The plist uses
the Python executable and repository path used during installation. Reinstall
after moving either one.

Check the agent with `launchctl print gui/$(id -u)/com.vasya.video-note-sync`.
Logs are in `~/Library/Logs/Vasya/video-note-sync.*.log`. Remove the agent with:

```bash
.venv/bin/python -m scripts.video_note_sync_launchd uninstall
```

If the server is unavailable, the run fails and the queued note remains for
the next run. Include the server queue database in backups; test restoring it
before treating the server as the only copy of pending transcripts.
