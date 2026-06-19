from __future__ import annotations

import argparse
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Render speech with optional CosyVoice TTS.")
    parser.add_argument("--repo-dir", required=True, help="Local FunAudioLLM/CosyVoice checkout.")
    parser.add_argument("--model-dir", required=True, help="Local CosyVoice model directory.")
    parser.add_argument("--text", required=True, help="Text to synthesize.")
    parser.add_argument("--output", required=True, help="Output WAV path.")
    parser.add_argument("--speaker", default="", help="Optional CosyVoice SFT speaker name.")
    args = parser.parse_args()

    repo_dir = Path(args.repo_dir).expanduser().resolve()
    model_dir = Path(args.model_dir).expanduser().resolve()
    if not repo_dir.exists():
        print(f"CosyVoice repo does not exist: {repo_dir}", file=sys.stderr)
        return 2
    if not model_dir.exists():
        print(f"CosyVoice model does not exist: {model_dir}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(repo_dir))
    matcha_dir = repo_dir / "third_party" / "Matcha-TTS"
    if matcha_dir.exists():
        sys.path.insert(0, str(matcha_dir))

    try:
        import torchaudio
        import cosyvoice.cli.cosyvoice as cosyvoice_module
    except Exception as exc:
        print(f"CosyVoice dependencies are not available: {exc}", file=sys.stderr)
        return 2

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cosyvoice = _load_model(model_dir, cosyvoice_module)
    speaker = args.speaker.strip() or _first_available_speaker(cosyvoice)
    if not speaker:
        print("CosyVoice SFT speaker is not configured and no speaker was available.", file=sys.stderr)
        return 2

    chunks = cosyvoice.inference_sft(args.text, speaker, stream=False)
    for chunk in chunks:
        speech = chunk.get("tts_speech")
        if speech is None:
            continue
        torchaudio.save(str(output_path), speech, cosyvoice.sample_rate)
        return 0

    print("CosyVoice completed without returning audio.", file=sys.stderr)
    return 1


def _load_model(model_dir: Path, cosyvoice_module: object) -> object:
    cosyvoice2_cls = getattr(cosyvoice_module, "CosyVoice2", None)
    cosyvoice_cls = getattr(cosyvoice_module, "CosyVoice", None)
    if cosyvoice_cls is None:
        raise RuntimeError("CosyVoice class was not found in cosyvoice.cli.cosyvoice")
    if cosyvoice2_cls is None:
        return cosyvoice_cls(str(model_dir), load_jit=False, load_trt=False, fp16=False)
    try:
        return cosyvoice2_cls(
            str(model_dir),
            load_jit=False,
            load_trt=False,
            load_vllm=False,
            fp16=False,
        )
    except Exception:
        return cosyvoice_cls(str(model_dir), load_jit=False, load_trt=False, fp16=False)


def _first_available_speaker(cosyvoice: object) -> str:
    speakers = getattr(cosyvoice, "list_available_spks", None)
    if callable(speakers):
        available = speakers()
        if available:
            return str(available[0])
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
