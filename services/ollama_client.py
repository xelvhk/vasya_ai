import subprocess
import time
import json
from urllib.parse import urlparse

import requests
from utils.platform_runtime import get_platform_name
from config.settings import (
    OLLAMA_CHAT_MODEL,
    OLLAMA_CHAT_MODEL_CANDIDATES,
    OLLAMA_FAST_MODEL,
    OLLAMA_MODEL,
    OLLAMA_URL,
)


class OllamaClientError(Exception):
    pass


_MODEL_CACHE: tuple[float, list[str]] | None = None


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
    except OSError:
        if get_platform_name() == "macos":
            try:
                subprocess.Popen(
                    ["open", "-a", "Ollama"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except OSError as exc:
                raise OllamaClientError(
                    "Не удалось запустить Ollama автоматически. Проверь, что Ollama установлена."
                ) from exc
        else:
            raise OllamaClientError(
                "Не удалось запустить Ollama автоматически. Проверь, что команда ollama доступна."
            )

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
    ensure_ollama_running()
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


def generate_stream(
    prompt: str,
    *,
    model: str | None = None,
    think: bool | str | None = None,
    temperature: float | None = None,
    num_predict: int | None = None,
):
    ensure_ollama_running()
    payload: dict = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
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
            stream=True,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OllamaClientError(
            f"Не удалось подключиться к Ollama по адресу {OLLAMA_URL}."
        ) from exc

    try:
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                data = json.loads(line)
            except ValueError as exc:
                raise OllamaClientError("Ollama вернул некорректный JSON stream.") from exc

            chunk = data.get("response", "")
            if isinstance(chunk, str) and chunk:
                yield chunk

            if data.get("done") is True:
                break
    finally:
        response.close()


def resolve_chat_model() -> str:
    configured = OLLAMA_CHAT_MODEL.strip()
    if configured and configured.lower() != "auto":
        return configured

    installed_models = get_installed_models()
    installed_names = {name.lower(): name for name in installed_models}
    for candidate in OLLAMA_CHAT_MODEL_CANDIDATES:
        resolved = installed_names.get(candidate.lower())
        if resolved is not None:
            return resolved
    return OLLAMA_FAST_MODEL


def get_installed_models(cache_ttl_seconds: float = 30.0) -> list[str]:
    global _MODEL_CACHE
    now = time.time()
    if _MODEL_CACHE is not None:
        cached_at, cached_models = _MODEL_CACHE
        if now - cached_at < cache_ttl_seconds:
            return list(cached_models)

    if not is_ollama_available():
        try:
            ensure_ollama_running()
        except OllamaClientError:
            return []

    try:
        response = requests.get(_healthcheck_url(), timeout=2)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    models = []
    for item in data.get("models", []):
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            models.append(name.strip())

    _MODEL_CACHE = (now, models)
    return list(models)


def _healthcheck_url() -> str:
    parsed = urlparse(OLLAMA_URL)
    return f"{parsed.scheme}://{parsed.netloc}/api/tags"
