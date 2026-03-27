import subprocess
import time
from urllib.parse import urlparse

import requests
from config.settings import OLLAMA_MODEL, OLLAMA_URL


class OllamaClientError(Exception):
    pass


def ensure_ollama_running(timeout_seconds: float = 10.0) -> bool:
    if is_ollama_available():
        return True

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise OllamaClientError(
            "Не удалось запустить Ollama автоматически. Проверь, что команда ollama доступна."
        ) from exc

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_ollama_available():
            return True
        time.sleep(0.5)

    raise OllamaClientError(
        "Ollama не запустился вовремя. Проверь локальный сервер и модель."
    )


def is_ollama_available() -> bool:
    try:
        response = requests.get(_healthcheck_url(), timeout=2)
        response.raise_for_status()
    except requests.RequestException:
        return False
    return True


def generate(
    prompt: str,
    *,
    model: str | None = None,
    think: bool | str | None = None,
    temperature: float | None = None,
    num_predict: int | None = None,
) -> str:
    payload: dict = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if think is not None:
        payload["think"] = think

    options: dict = {}
    if temperature is not None:
        options["temperature"] = temperature
    if num_predict is not None:
        options["num_predict"] = num_predict
    if options:
        payload["options"] = options

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OllamaClientError(
            f"Не удалось подключиться к Ollama по адресу {OLLAMA_URL}."
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise OllamaClientError("Ollama вернул некорректный JSON.") from exc

    result = data.get("response")
    if not isinstance(result, str):
        raise OllamaClientError("В ответе Ollama нет текстового поля response.")

    return result.strip()


def _healthcheck_url() -> str:
    parsed = urlparse(OLLAMA_URL)
    return f"{parsed.scheme}://{parsed.netloc}/api/tags"
