"""Pull pending video transcripts from Vasya server into this Mac's Obsidian vault."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys
from urllib.parse import urlparse
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from services.allowed_knowledge_service import resolve_knowledge_vault_path
from services.video_note_service import VideoNoteError, save_video_note


def sync_once(server: str, api_key: str, vault: Path) -> tuple[int, int]:
    base = validate_server_url(server)
    if not api_key:
        raise ValueError("VASYA_VIDEO_NOTE_SYNC_API_KEY is required")
    items = _request_json(f"{base}/v1/video/pending-notes", api_key)["items"]
    saved_count = failed_count = 0
    for item in items:
        try:
            saved = save_video_note(
                video_id=item["video_id"], source_url=item.get("source_url"),
                summary=item["summary"], subtitle_srt=item["subtitle_srt"],
                subtitle_origin=item["subtitle_origin"], vault_path=vault,
            )
            _request_json(
                f"{base}/v1/video/pending-notes/{item['video_id']}/complete", api_key,
                {"revision": item["revision"], "relative_path": saved.relative_path,
                 "url": saved.url},
            )
            saved_count += 1
        except (VideoNoteError, OSError, ValueError) as exc:
            print(f"video note {item.get('video_id', 'unknown')[:12]}: {exc}", file=sys.stderr)
            failed_count += 1
    return saved_count, failed_count


def validate_server_url(server: str) -> str:
    base = server.rstrip("/")
    parsed = urlparse(base)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Invalid server URL")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Use HTTPS or a local tunnel for private transcripts")
    return base


def read_api_key_file(path: Path) -> str:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError("API key file must not be a symbolic link")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, encoding="utf-8") as handle:
        metadata = os.fstat(handle.fileno())
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o077
        ):
            raise ValueError("API key file must be an owner-only regular file")
        api_key = handle.read().strip()
    if not api_key:
        raise ValueError("API key file is empty")
    return api_key


def _request_json(url: str, api_key: str, body: dict | None = None) -> dict:
    request = Request(
        url, method="POST" if body is not None else "GET",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
    )
    with build_opener(_NoRedirect()).open(request, timeout=30) as response:
        return json.load(response)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise HTTPError(request.full_url, code, "Redirect refused for private note sync", headers, fp)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True, help="HTTPS server or localhost tunnel URL")
    parser.add_argument("--vault", type=Path, default=resolve_knowledge_vault_path())
    parser.add_argument("--api-key-file", type=Path, help="Owner-only file containing the sync API key")
    args = parser.parse_args()
    saved, failed = sync_once(
        args.server,
        read_api_key_file(args.api_key_file) if args.api_key_file else os.getenv(
            "VASYA_VIDEO_NOTE_SYNC_API_KEY", ""
        ),
        args.vault,
    )
    print(f"Saved {saved} video notes; failed {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
