"""Install the official Silero v5.5 Russian model outside Git."""

from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import SILERO_MODEL_PATH  # noqa: E402


MODEL_URL = "https://models.silero.ai/models/tts/ru/v5_5_ru.pt"
MODEL_SHA256 = "50081637b602126ee06cb3bc8a744d25651d2da149ee8864b9a379bfdd934437"


def main() -> None:
    destination = Path(SILERO_MODEL_PATH).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    print("Silero v5.5 is licensed under CC BY-NC-SA 4.0; use it only within those terms.")
    print("License: https://github.com/snakers4/silero-models/blob/master/LICENSE")
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".part", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        digest = hashlib.sha256()
        try:
            with urlopen(MODEL_URL, timeout=60) as response:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    temp_file.write(chunk)
                    digest.update(chunk)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
    if digest.hexdigest() != MODEL_SHA256:
        temp_path.unlink(missing_ok=True)
        raise RuntimeError("Silero model checksum mismatch; nothing was installed.")
    temp_path.replace(destination)
    print(f"Installed Silero model: {destination}")


if __name__ == "__main__":
    main()
