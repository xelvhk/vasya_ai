from __future__ import annotations

import argparse
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Render speech with optional Chatterbox TTS.")
    parser.add_argument("--text", required=True, help="Text to synthesize.")
    parser.add_argument("--output", required=True, help="Output WAV path.")
    parser.add_argument("--language", default="ru", help="Chatterbox language_id.")
    parser.add_argument("--t3-model", default="v3", help="Multilingual T3 model variant.")
    parser.add_argument("--device", default="auto", help="Torch device: auto, cuda, mps, or cpu.")
    args = parser.parse_args()

    try:
        import torch
        import torchaudio as ta
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except Exception as exc:
        print(f"Chatterbox dependencies are not available: {exc}", file=sys.stderr)
        return 2

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    device = _resolve_device(args.device, torch)
    model = ChatterboxMultilingualTTS.from_pretrained(
        device=device,
        t3_model=args.t3_model,
    )
    wav = model.generate(args.text, language_id=args.language)
    ta.save(str(output_path), wav, model.sr)
    return 0


def _resolve_device(requested: str, torch_module: object) -> str:
    normalized = requested.strip().lower()
    if normalized != "auto":
        return normalized
    if torch_module.cuda.is_available():
        return "cuda"
    if getattr(torch_module.backends, "mps", None) is not None and torch_module.backends.mps.is_available():
        return "mps"
    return "cpu"


if __name__ == "__main__":
    raise SystemExit(main())
