from __future__ import annotations

import requests

from config.settings import (
    NOTION_API_BASE_URL,
    NOTION_API_TOKEN,
    NOTION_API_VERSION,
)
from services.integration_settings_service import get_integration_setting


class NotionServiceError(Exception):
    pass


def append_markdown_like_entry(page_id: str, title: str, lines: list[str]) -> None:
    normalized_page_id = _normalize_page_id(page_id)
    if not normalized_page_id:
        raise NotionServiceError("Не указан NOTION_UPDATES_PAGE_ID.")
    token = get_integration_setting("notion_api_token") or NOTION_API_TOKEN
    if not token:
        raise NotionServiceError("Не указан NOTION_API_TOKEN.")

    blocks: list[dict] = [
        _heading_block(title),
    ]
    for line in lines:
        text = " ".join(str(line).strip().split())
        if not text:
            continue
        blocks.append(_bulleted_block(text))
    blocks.append({"object": "block", "type": "divider", "divider": {}})

    response = requests.patch(
        f"{NOTION_API_BASE_URL}/blocks/{normalized_page_id}/children",
        headers=_headers(token),
        json={"children": blocks},
        timeout=20,
    )
    if response.status_code >= 400:
        raise NotionServiceError(_format_error("Notion append", response))


def read_page_text(page_id: str, *, limit: int = 25) -> list[str]:
    normalized_page_id = _normalize_page_id(page_id)
    if not normalized_page_id:
        raise NotionServiceError("Не указан NOTION_UPDATES_PAGE_ID.")
    token = get_integration_setting("notion_api_token") or NOTION_API_TOKEN
    if not token:
        raise NotionServiceError("Не указан NOTION_API_TOKEN.")

    response = requests.get(
        f"{NOTION_API_BASE_URL}/blocks/{normalized_page_id}/children",
        headers=_headers(token),
        params={"page_size": max(1, min(limit, 100))},
        timeout=20,
    )
    if response.status_code >= 400:
        raise NotionServiceError(_format_error("Notion read", response))
    payload = response.json()
    results = payload.get("results", []) if isinstance(payload, dict) else []
    if not isinstance(results, list):
        return []

    lines: list[str] = []
    for block in results:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("type", ""))
        content = block.get(block_type, {})
        if not isinstance(content, dict):
            continue
        rich = content.get("rich_text", [])
        if not isinstance(rich, list):
            continue
        text = "".join(
            str(node.get("plain_text", ""))
            for node in rich
            if isinstance(node, dict)
        ).strip()
        if text:
            lines.append(text)
    return lines


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def _normalize_page_id(page_id: str) -> str:
    return str(page_id).strip().replace("-", "")


def _heading_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": text[:200]}}],
        },
    }


def _bulleted_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text[:1800]}}],
        },
    }


def _format_error(label: str, response: requests.Response) -> str:
    try:
        payload = response.json()
        message = payload.get("message", "") if isinstance(payload, dict) else ""
    except ValueError:
        message = ""
    details = f": {message}" if message else ""
    return f"{label} API вернул {response.status_code}{details}"
