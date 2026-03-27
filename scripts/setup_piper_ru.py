from __future__ import annotations

import argparse
from pathlib import Path
from shutil import copy2

from huggingface_hub import hf_hub_download


REPO_ID = "rhasspy/piper-voices"
RUSSIAN_VOICES = {
    "irina": ("ru/ru_RU/irina/medium", "ru_RU-irina-medium.onnx"),
    "ruslan": ("ru/ru_RU/ruslan/medium", "ru_RU-ruslan-medium.onnx"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Russian Piper voice models")
    parser.add_argument(
        "--voices",
        nargs="+",
        default=["ruslan"],
        help="Voice ids to download: ruslan or all",
    )
    args = parser.parse_args()

    requested_voices = args.voices
    if "all" in requested_voices:
        requested_voices = list(RUSSIAN_VOICES.keys())

    target_dir = Path("storage/voices")
    target_dir.mkdir(parents=True, exist_ok=True)

    for voice_id in requested_voices:
        voice_spec = RUSSIAN_VOICES.get(voice_id)
        if voice_spec is None:
            print(f"Skipping unknown voice: {voice_id}")
            continue
        _download_voice(target_dir, voice_id, *voice_spec)


def _download_voice(target_dir: Path, voice_id: str, voice_dir: str, model_name: str) -> None:
    config_name = f"{model_name}.json"
    print(f"Downloading Russian Piper voice model: {voice_id}")
    model_path = hf_hub_download(
        repo_id=REPO_ID,
        filename=f"{voice_dir}/{model_name}",
        local_dir=target_dir,
        local_dir_use_symlinks=False,
    )
    config_path = hf_hub_download(
        repo_id=REPO_ID,
        filename=f"{voice_dir}/{config_name}",
        local_dir=target_dir,
        local_dir_use_symlinks=False,
    )

    model_target = target_dir / model_name
    config_target = target_dir / config_name
    copy2(model_path, model_target)
    copy2(config_path, config_target)

    print(f"Model saved to: {model_target}")
    print(f"Config saved to: {config_target}")


if __name__ == "__main__":
    main()
