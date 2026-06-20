from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Render speech with Coqui XTTS using project-local caches.")
    parser.add_argument("--model-name", required=True, help="Coqui TTS model name.")
    parser.add_argument("--text", required=True, help="Text to synthesize.")
    parser.add_argument("--speaker-wav", required=True, help="Trusted local speaker WAV.")
    parser.add_argument("--language", default="ru", help="XTTS language index.")
    parser.add_argument("--output", required=True, help="Output WAV path.")
    parser.add_argument("--cache-dir", required=True, help="Project-local Coqui TTS cache directory.")
    parser.add_argument("--mplconfig-dir", required=True, help="Writable matplotlib cache directory.")
    parser.add_argument("--xdg-cache-dir", required=True, help="Writable XDG cache directory.")
    parser.add_argument(
        "--trust-local-checkpoint",
        action="store_true",
        help="Allow Coqui XTTS checkpoints from the configured local cache to use PyTorch non-weights-only load.",
    )
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir).expanduser().resolve()
    mplconfig_dir = Path(args.mplconfig_dir).expanduser().resolve()
    xdg_cache_dir = Path(args.xdg_cache_dir).expanduser().resolve()
    hf_cache_dir = cache_dir / "hf_cache"
    output_path = Path(args.output)
    speaker_wav = Path(args.speaker_wav).expanduser().resolve()

    for path in (cache_dir, mplconfig_dir, xdg_cache_dir, hf_cache_dir, output_path.parent):
        path.mkdir(parents=True, exist_ok=True)

    if not speaker_wav.exists():
        print(f"XTTS speaker WAV does not exist: {speaker_wav}", file=sys.stderr)
        return 2

    os.environ.setdefault("TTS_HOME", str(cache_dir))
    os.environ.setdefault("XDG_DATA_HOME", str(cache_dir))
    os.environ.setdefault("MPLCONFIGDIR", str(mplconfig_dir))
    os.environ.setdefault("XDG_CACHE_HOME", str(xdg_cache_dir))
    os.environ.setdefault("HF_HOME", str(hf_cache_dir))
    os.environ.setdefault("COQUI_TOS_AGREED", "1")

    if args.trust_local_checkpoint:
        # Trust boundary: Coqui XTTS checkpoints are loaded through torch.load. PyTorch 2.6+
        # defaults to weights_only=True, which rejects XTTS config classes. This opt-out is
        # acceptable only for checkpoints the user intentionally keeps in the project-local
        # XTTS cache and trusts. Do not enable it for arbitrary downloaded files.
        os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

    try:
        from TTS.bin.synthesize import main as tts_main
    except Exception as exc:
        print(f"Coqui TTS is not available in this Python environment: {exc}", file=sys.stderr)
        return 2

    sys.argv = [
        "tts",
        "--model_name",
        args.model_name,
        "--text",
        args.text,
        "--speaker_wav",
        str(speaker_wav),
        "--language_idx",
        args.language,
        "--out_path",
        str(output_path),
    ]
    return int(tts_main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
