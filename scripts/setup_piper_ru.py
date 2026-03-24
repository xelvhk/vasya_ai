from __future__ import annotations

from pathlib import Path
from shutil import copy2

from huggingface_hub import hf_hub_download


REPO_ID = "rhasspy/piper-voices"
VOICE_DIR = "ru/ru_RU/irina/medium"
MODEL_NAME = "ru_RU-irina-medium.onnx"
CONFIG_NAME = "ru_RU-irina-medium.onnx.json"


def main() -> None:
    target_dir = Path("storage/voices")
    target_dir.mkdir(parents=True, exist_ok=True)

    print("Downloading Russian Piper voice model...")
    model_path = hf_hub_download(
        repo_id=REPO_ID,
        filename=f"{VOICE_DIR}/{MODEL_NAME}",
        local_dir=target_dir,
        local_dir_use_symlinks=False,
    )
    config_path = hf_hub_download(
        repo_id=REPO_ID,
        filename=f"{VOICE_DIR}/{CONFIG_NAME}",
        local_dir=target_dir,
        local_dir_use_symlinks=False,
    )

    model_target = target_dir / MODEL_NAME
    config_target = target_dir / CONFIG_NAME
    copy2(model_path, model_target)
    copy2(config_path, config_target)

    print(f"Model saved to: {model_target}")
    print(f"Config saved to: {config_target}")


if __name__ == "__main__":
    main()
