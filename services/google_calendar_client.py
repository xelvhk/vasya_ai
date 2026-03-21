from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from config.settings import (
    GOOGLE_CALENDAR_CREDENTIALS_FILE,
    GOOGLE_CALENDAR_DEFAULT_EVENT_DURATION_MINUTES,
    GOOGLE_CALENDAR_ENABLED,
    GOOGLE_CALENDAR_ID,
    GOOGLE_CALENDAR_READ_MAX_RESULTS,
    GOOGLE_CALENDAR_TIMEZONE,
    GOOGLE_CALENDAR_TOKEN_FILE,
)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class GoogleCalendarError(Exception):
    pass


def create_google_calendar_event(title: str, dt: str) -> str:
    if not GOOGLE_CALENDAR_ENABLED:
        raise GoogleCalendarError("Google Calendar integration is disabled.")

    service = _build_service()
    start_datetime = datetime.strptime(dt, "%Y-%m-%d %H:%M")
    end_datetime = start_datetime + timedelta(
        minutes=GOOGLE_CALENDAR_DEFAULT_EVENT_DURATION_MINUTES
    )

    event_body = {
        "summary": title,
        "start": {
            "dateTime": start_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": GOOGLE_CALENDAR_TIMEZONE,
        },
        "end": {
            "dateTime": end_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": GOOGLE_CALENDAR_TIMEZONE,
        },
    }

    try:
        created_event = (
            service.events()
            .insert(calendarId=GOOGLE_CALENDAR_ID, body=event_body)
            .execute()
        )
    except Exception as exc:
        raise GoogleCalendarError(
            f"Failed to create event in Google Calendar: {exc}"
        ) from exc
    event_id = created_event.get("id")
    if not event_id:
        raise GoogleCalendarError("Google Calendar did not return an event id.")

    return event_id


def list_google_calendar_events() -> list[dict]:
    if not GOOGLE_CALENDAR_ENABLED:
        raise GoogleCalendarError("Google Calendar integration is disabled.")

    service = _build_service()

    try:
        response = (
            service.events()
            .list(
                calendarId=GOOGLE_CALENDAR_ID,
                timeMin=datetime.now(timezone.utc).isoformat(),
                maxResults=GOOGLE_CALENDAR_READ_MAX_RESULTS,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except Exception as exc:
        raise GoogleCalendarError(
            f"Failed to fetch events from Google Calendar: {exc}"
        ) from exc

    items = response.get("items", [])
    return [_map_google_event(item) for item in items if item.get("id")]


def _build_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GoogleCalendarError(
            "Google Calendar dependencies are not installed."
        ) from exc

    creds = None
    if os.path.exists(GOOGLE_CALENDAR_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GOOGLE_CALENDAR_TOKEN_FILE, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not os.path.exists(GOOGLE_CALENDAR_CREDENTIALS_FILE):
            raise GoogleCalendarError(
                f"Credentials file not found: {GOOGLE_CALENDAR_CREDENTIALS_FILE}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            GOOGLE_CALENDAR_CREDENTIALS_FILE,
            SCOPES,
        )
        creds = flow.run_local_server(port=0)
        _ensure_token_dir()
        with open(GOOGLE_CALENDAR_TOKEN_FILE, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def _ensure_token_dir() -> None:
    token_dir = os.path.dirname(GOOGLE_CALENDAR_TOKEN_FILE)
    if token_dir:
        os.makedirs(token_dir, exist_ok=True)


def _map_google_event(item: dict) -> dict:
    start_data = item.get("start", {})
    start_datetime = start_data.get("dateTime")
    start_date = start_data.get("date")

    normalized_datetime = None
    if start_datetime:
        normalized_datetime = datetime.fromisoformat(
            start_datetime.replace("Z", "+00:00")
        ).strftime("%Y-%m-%d %H:%M")
    elif start_date:
        normalized_datetime = f"{start_date} 00:00"

    return {
        "external_id": item["id"],
        "title": item.get("summary") or "Без названия",
        "datetime": normalized_datetime,
        "source": "google_calendar",
    }
