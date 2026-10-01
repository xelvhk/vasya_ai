# Video agent MVP

## Goal and contract

`@video` accepts one public Instagram Reel/post URL through `POST /v1/chat`
(`agent=video`) or a local media file through the authenticated raw-body endpoint
`POST /v1/video/upload` (raw body, `x-video-extension` and optional
percent-encoded `x-video-question` headers). Both return the existing `ChatResponse` shape with a
timestamped transcript, a concise answer when the local model is available,
and a source URL for link inputs. No account cookies or cloud transcription are
used. A Telegram attachment can later call the same upload service.

## Processing

1. Accept only canonical `https://www.instagram.com/{reel,p,tv}/ID/` links.
   Download one public video with yt-dlp, bounded by size and time. An
   inaccessible post returns a clear error and asks for a file.
2. Accept media file uploads up to 100 MiB; keep them in a temporary directory
   for the request, then delete them. Verify media duration (at most 15 minutes)
   and an audio stream with ffprobe.
3. Prefer an available SRT/VTT subtitle track from yt-dlp. Otherwise extract
   audio with ffmpeg and use Vasya's existing faster-whisper model, retaining
   segment timestamps.
4. Ask local Ollama for one concise answer. Validate that its cited quote occurs
   in the chosen transcript segment. If unavailable or invalid, show the
   timestamped transcript without pretending to have a summary.

## Verification

- Unit tests: URL allowlist, inaccessible URL fallback, upload limits, subtitle
  parser, transcript and citation validation.
- API tests: auth, link and file routes using mocked media/model components.
- Full unittest suite and a local ffprobe/ffmpeg smoke check.

## Boundaries

This MVP processes the audio/subtitle content; text burned into frames and
visual scene analysis are a later OCR/vision slice. It does not access private
Instagram posts, browser cookies, arbitrary URLs, or user filesystem paths.
