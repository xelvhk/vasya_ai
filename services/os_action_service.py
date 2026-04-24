from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from assistant.confirmations import confirmation_store
from config.settings import (
    OS_ACTIONS_ENABLED,
    OS_ALLOWED_APPS,
    OS_ALLOWED_URL_DOMAINS,
    OS_REQUIRE_CONFIRM_FOR_INPUT,
    OS_REQUIRE_CONFIRM_FOR_OPEN_EXTERNAL,
)
from utils.logger import log_interaction_event


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    reason: str = ""
    normalized_payload: dict[str, Any] | None = None
    requires_confirmation: bool = False
    preview: str = ""


def execute_os_action(
    action: str,
    payload: dict[str, Any] | None = None,
    *,
    skip_confirmation: bool = False,
) -> str:
    payload = payload or {}
    observed = _observe_environment()
    if not observed["enabled"]:
        return "OS-управление выключено в настройках окружения."

    decision = _decide_action(action, payload, observed)
    if not decision.allowed:
        return decision.reason or "Действие не разрешено."

    normalized_payload = decision.normalized_payload or {}
    if decision.requires_confirmation and not skip_confirmation:
        confirmation_store.set(
            "os_action",
            {"action": action, "payload": normalized_payload},
        )
        return (
            f"Подтверди действие: {decision.preview}. "
            "Скажи да или нет."
        )

    result = _act(action, normalized_payload, observed)
    _verify_action(action, normalized_payload, result)
    return result


def confirm_os_action(payload: dict[str, Any]) -> str:
    action = str(payload.get("action", "")).strip()
    action_payload = payload.get("payload")
    if not action or not isinstance(action_payload, dict):
        return "Подтверждение сброшено: не удалось прочитать действие."
    return execute_os_action(action, action_payload, skip_confirmation=True)


def _observe_environment() -> dict[str, Any]:
    return {
        "enabled": OS_ACTIONS_ENABLED,
        "platform": sys.platform,
        "allowed_domains": _parse_csv_list(OS_ALLOWED_URL_DOMAINS),
        "allowed_apps": _parse_csv_list(OS_ALLOWED_APPS),
    }


def _decide_action(
    action: str,
    payload: dict[str, Any],
    observed: dict[str, Any],
) -> ActionDecision:
    if action == "open_url":
        raw_url = str(payload.get("url", "")).strip()
        if not raw_url:
            return ActionDecision(False, "Не передан URL для открытия.")
        normalized_url = _normalize_url(raw_url)
        parsed = urlparse(normalized_url)
        if parsed.scheme not in {"http", "https"}:
            return ActionDecision(False, "Разрешены только http/https ссылки.")
        host = (parsed.hostname or "").lower()
        if not host:
            return ActionDecision(False, "Не удалось распознать домен ссылки.")
        if not _is_allowed_domain(host, observed["allowed_domains"]):
            return ActionDecision(
                False,
                "Этот домен не входит в allowlist. Добавь его в OS_ALLOWED_URL_DOMAINS.",
            )
        return ActionDecision(
            True,
            normalized_payload={"url": normalized_url},
            requires_confirmation=OS_REQUIRE_CONFIRM_FOR_OPEN_EXTERNAL,
            preview=f"открыть сайт {normalized_url}",
        )

    if action == "open_app":
        app = str(payload.get("app", "")).strip()
        if not app:
            return ActionDecision(False, "Не указано приложение для открытия.")
        normalized_app = app.strip()
        if not _is_allowed_app(normalized_app, observed["allowed_apps"]):
            return ActionDecision(
                False,
                "Это приложение не входит в allowlist. Добавь его в OS_ALLOWED_APPS.",
            )
        return ActionDecision(
            True,
            normalized_payload={"app": normalized_app},
            requires_confirmation=False,
            preview=f"открыть приложение {normalized_app}",
        )

    if action == "type_text":
        text = str(payload.get("text", ""))
        if not text.strip():
            return ActionDecision(False, "Не передан текст для ввода.")
        return ActionDecision(
            True,
            normalized_payload={"text": text},
            requires_confirmation=OS_REQUIRE_CONFIRM_FOR_INPUT,
            preview=f"ввести текст: {text[:60]}",
        )

    if action == "keypress":
        keys = _normalize_keys(payload.get("keys"))
        if not keys:
            return ActionDecision(False, "Не переданы клавиши для нажатия.")
        return ActionDecision(
            True,
            normalized_payload={"keys": keys},
            requires_confirmation=OS_REQUIRE_CONFIRM_FOR_INPUT,
            preview=f"нажать клавиши: {' + '.join(keys)}",
        )

    if action == "click":
        button = str(payload.get("button", "left")).strip().lower() or "left"
        if button not in {"left", "right", "middle"}:
            return ActionDecision(False, "Поддерживаются кнопки left/right/middle.")
        clicks_raw = payload.get("clicks", 1)
        clicks = int(clicks_raw) if str(clicks_raw).strip().isdigit() else 1
        clicks = max(1, min(clicks, 3))
        return ActionDecision(
            True,
            normalized_payload={"button": button, "clicks": clicks},
            requires_confirmation=OS_REQUIRE_CONFIRM_FOR_INPUT,
            preview=f"кликнуть {button} ({clicks}x)",
        )

    if action == "scroll":
        amount_raw = payload.get("amount", -500)
        try:
            amount = int(float(str(amount_raw).strip()))
        except ValueError:
            amount = -500
        if amount == 0:
            amount = -500
        amount = max(-2500, min(amount, 2500))
        direction = "вниз" if amount < 0 else "вверх"
        return ActionDecision(
            True,
            normalized_payload={"amount": amount},
            requires_confirmation=OS_REQUIRE_CONFIRM_FOR_INPUT,
            preview=f"прокрутить {direction} ({abs(amount)})",
        )

    return ActionDecision(False, "Неизвестное OS-действие.")


def _act(action: str, payload: dict[str, Any], observed: dict[str, Any]) -> str:
    platform = str(observed.get("platform", ""))
    if action == "open_url":
        _open_target(payload["url"], platform=platform, is_app=False)
        return f"Открываю: {payload['url']}"

    if action == "open_app":
        _open_target(payload["app"], platform=platform, is_app=True)
        return f"Открываю приложение: {payload['app']}"

    if action == "type_text":
        keyboard = _keyboard_controller()
        keyboard.type(payload["text"])
        return "Ввела текст в активное поле."

    if action == "keypress":
        keyboard_module = _keyboard_module()
        keyboard = keyboard_module.Controller()
        resolved = [_resolve_key_name(name, keyboard_module) for name in payload["keys"]]
        if len(resolved) == 1:
            key = resolved[0]
            keyboard.press(key)
            keyboard.release(key)
            return "Нажала клавишу."

        for key in resolved[:-1]:
            keyboard.press(key)
        keyboard.press(resolved[-1])
        keyboard.release(resolved[-1])
        for key in reversed(resolved[:-1]):
            keyboard.release(key)
        return "Нажала сочетание клавиш."

    if action == "click":
        mouse_module = _mouse_module()
        mouse = mouse_module.Controller()
        button = getattr(mouse_module.Button, payload["button"])
        mouse.click(button, payload["clicks"])
        return "Клик выполнен."

    if action == "scroll":
        mouse = _mouse_module().Controller()
        mouse.scroll(0, payload["amount"])
        return "Прокрутка выполнена."

    raise RuntimeError("Unsupported action")


def _verify_action(action: str, payload: dict[str, Any], result: str) -> None:
    log_interaction_event(
        "os_action",
        {
            "action": action,
            "payload": payload,
            "result": result,
        },
    )


def _open_target(target: str, *, platform: str, is_app: bool) -> None:
    try:
        if platform == "darwin":
            if is_app:
                subprocess.run(["open", "-a", target], check=True)
            else:
                subprocess.run(["open", target], check=True)
            return

        if platform.startswith("linux"):
            subprocess.run(["xdg-open", target], check=True)
            return

        if platform.startswith("win"):
            if is_app:
                subprocess.run(["cmd", "/c", "start", "", target], check=True)
            else:
                subprocess.run(["cmd", "/c", "start", "", target], check=True)
            return
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc
    raise RuntimeError("Неподдерживаемая платформа для этого действия.")


def _keyboard_module():
    from pynput import keyboard

    return keyboard


def _mouse_module():
    from pynput import mouse

    return mouse


def _keyboard_controller():
    return _keyboard_module().Controller()


def _resolve_key_name(name: str, keyboard_module: Any):
    normalized = name.strip().lower()
    aliases = {
        "cmd": "cmd",
        "command": "cmd",
        "meta": "cmd",
        "win": "cmd",
        "ctrl": "ctrl",
        "control": "ctrl",
        "alt": "alt",
        "option": "alt",
        "shift": "shift",
        "enter": "enter",
        "return": "enter",
        "esc": "esc",
        "escape": "esc",
        "tab": "tab",
        "space": "space",
        "пробел": "space",
        "backspace": "backspace",
        "delete": "delete",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
    }
    key_name = aliases.get(normalized, normalized)
    if len(key_name) == 1:
        return key_name
    try:
        return getattr(keyboard_module.Key, key_name)
    except AttributeError as exc:
        raise RuntimeError(f"Неподдерживаемая клавиша: {name}") from exc


def _normalize_url(value: str) -> str:
    candidate = value.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    return candidate


def _is_allowed_domain(host: str, allowed_domains: list[str]) -> bool:
    host = host.lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    for domain in allowed_domains:
        normalized = domain.lower().strip().strip(".")
        if not normalized:
            continue
        if host == normalized or host.endswith(f".{normalized}"):
            return True
    return False


def _is_allowed_app(app_name: str, allowed_apps: list[str]) -> bool:
    normalized = app_name.strip().lower()
    return any(normalized == app.lower().strip() for app in allowed_apps)


def _normalize_keys(raw_keys: Any) -> list[str]:
    if isinstance(raw_keys, list):
        keys = [str(item).strip() for item in raw_keys if str(item).strip()]
        return keys
    if isinstance(raw_keys, str):
        candidate = raw_keys.strip()
        if not candidate:
            return []
        splitter = "+" if "+" in candidate else " "
        keys = [part.strip() for part in candidate.split(splitter) if part.strip()]
        return keys
    return []


def _parse_csv_list(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]
