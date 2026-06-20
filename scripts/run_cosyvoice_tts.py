from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Render speech with optional CosyVoice TTS.")
    parser.add_argument("--repo-dir", required=True, help="Local FunAudioLLM/CosyVoice checkout.")
    parser.add_argument("--model-dir", required=True, help="Local CosyVoice model directory.")
    parser.add_argument("--text", required=True, help="Text to synthesize.")
    parser.add_argument("--output", required=True, help="Output WAV path.")
    parser.add_argument("--speaker", default="", help="Optional CosyVoice SFT speaker name.")
    parser.add_argument("--prompt-wav", default="", help="Prompt WAV for CosyVoice3/zero-shot synthesis.")
    parser.add_argument("--prompt-text", default="", help="Transcript or style prompt paired with --prompt-wav.")
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
        from cosyvoice.cli.cosyvoice import AutoModel
    except Exception as exc:
        print(f"CosyVoice dependencies are not available: {exc}", file=sys.stderr)
        return 2

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    runner_cache_dir = output_path.parent.parent / "cache" / "cosyvoice"
    runner_hf_dir = runner_cache_dir / "hf_home"
    runner_mpl_dir = output_path.parent.parent / "mpl_cache"
    for cache_path in (runner_cache_dir, runner_hf_dir, runner_mpl_dir):
        cache_path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("XDG_CACHE_HOME", str(runner_cache_dir))
    os.environ.setdefault("HF_HOME", str(runner_hf_dir))
    os.environ.setdefault("MPLCONFIGDIR", str(runner_mpl_dir))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    cosyvoice = AutoModel(
        model_dir=str(model_dir),
        load_trt=False,
        load_vllm=False,
        fp16=False,
    )
    if _is_cosyvoice3_model(model_dir):
        prompt_wav = Path(args.prompt_wav).expanduser().resolve() if args.prompt_wav else None
        if prompt_wav is None or not prompt_wav.exists():
            print("CosyVoice3 requires a trusted local --prompt-wav for zero-shot synthesis.", file=sys.stderr)
            return 2
        prompt_text = _cosyvoice3_prompt_text(args.prompt_text)
        if not prompt_text:
            print("CosyVoice3 requires --prompt-text paired with --prompt-wav.", file=sys.stderr)
            return 2
        chunks = cosyvoice.inference_zero_shot(
            args.text,
            prompt_text,
            str(prompt_wav),
            stream=False,
        )
    else:
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


def _is_cosyvoice3_model(model_dir: Path) -> bool:
    return (model_dir / "cosyvoice3.yaml").exists()


def _cosyvoice3_prompt_text(prompt_text: str) -> str:
    cleaned = prompt_text.strip()
    if cleaned and "<|endofprompt|>" not in cleaned:
        return f"{cleaned}<|endofprompt|>"
    return cleaned


def _first_available_speaker(cosyvoice: object) -> str:
    speakers = getattr(cosyvoice, "list_available_spks", None)
    if callable(speakers):
        available = speakers()
        if available:
            return str(available[0])
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
