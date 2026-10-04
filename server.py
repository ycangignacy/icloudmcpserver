"""Local iCloud Calendar MCP server. All project and event backups stay in this folder."""

from __future__ import annotations

import hashlib
import os
import re
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from caldav import DAVClient
from dotenv import load_dotenv
from icalendar import Calendar as ICalendar
from mcp.server.fastmcp import FastMCP


ROOT = Path(__file__).resolve().parent
BACKUPS = ROOT / "kopie zapasowe" / "wydarzenia"
load_dotenv(ROOT / ".env.local")
mcp = FastMCP("Apple Calendar (iCloud)")


def _parse_time(value: str) -> date | datetime:
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError("Timed events require a UTC offset, such as +02:00.")
        return result
    except ValueError as exc:
        raise ValueError(f"Invalid date/time: {value}. Use YYYY-MM-DD or ISO 8601 with a UTC offset.") from exc


def _range(start: str, end: str) -> tuple[date | datetime, date | datetime]:
    first, last = _parse_time(start), _parse_time(end)
    if isinstance(first, datetime) != isinstance(last, datetime):
        raise ValueError("Start and end must both be dates or both be timed values.")
    if first >= last:
        raise ValueError("End must be later than start.")
    return first, last


@contextmanager
def _client() -> Iterator[DAVClient]:
    username = os.getenv("APPLE_ID", "").strip()
    password = os.getenv("APPLE_APP_PASSWORD", "").strip()
    if not username or not password:
        raise ValueError("Set APPLE_ID and APPLE_APP_PASSWORD in .env.local.")
    url = os.getenv("APPLE_CALDAV_URL", "https://caldav.icloud.com").strip()
    if not url.startswith("https://"):
        raise ValueError("APPLE_CALDAV_URL must use HTTPS.")
    with DAVClient(url=url, username=username, password=password) as client:
        yield client


def _calendars(client: DAVClient) -> list[Any]:
    return client.principal().get_calendars()


def _calendar(client: DAVClient, calendar_id: str) -> Any:
    for calendar in _calendars(client):
        if str(calendar.url) == calendar_id:
            return calendar
    raise ValueError("Calendar not found. Call list_calendars to get a current ID.")


def _component(event: Any) -> Any:
    components = [item for item in ICalendar.from_ical(event.data).walk() if item.name == "VEVENT"]
    master = next((item for item in components if "RECURRENCE-ID" not in item), None)
    if not components:
        raise ValueError("VEVENT component not found.")
    return master or components[0]


def _as_iso(value: Any) -> str | None:
    if value is None:
        return None
    decoded = value.dt if hasattr(value, "dt") else value
    return decoded.isoformat() if hasattr(decoded, "isoformat") else str(decoded)


def _event_info(event: Any, calendar_id: str) -> dict[str, Any]:
    item = _component(event)
    return {
        "calendar_id": calendar_id,
        "uid": str(item.get("UID", "")),
        "title": str(item.get("SUMMARY", "")),
        "start": _as_iso(item.get("DTSTART")),
        "end": _as_iso(item.get("DTEND")),
        "description": str(item.get("DESCRIPTION", "")),
        "location": str(item.get("LOCATION", "")),
        "recurring": "RRULE" in item or "RECURRENCE-ID" in item,
        "recurrence_id": _as_iso(item.get("RECURRENCE-ID")),
        "url": str(event.url),
    }


def _backup(event: Any, action: str) -> str:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    uid = str(_component(event).get("UID", "unknown"))
    digest = hashlib.sha256(uid.encode("utf-8")).hexdigest()[:12]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = BACKUPS / f"{stamp}_{action}_{digest}_{uuid4().hex[:8]}.ics"
    with path.open("x", encoding="utf-8", newline="") as output:
        output.write(event.data)
    return str(path)


@mcp.tool()
def list_calendars() -> list[dict[str, Any]]:
    """List iCloud calendars and their IDs. Use an ID for other tools."""
    with _client() as client:
        return [{"id": str(cal.url), "name": str(cal.name or "")}
                for cal in _calendars(client)]


@mcp.tool()
def list_events(calendar_id: str, start: str, end: str) -> list[dict[str, Any]]:
    """List event occurrences in a time range. Dates are YYYY-MM-DD; end is exclusive."""
    first, last = _range(start, end)
    with _client() as client:
        calendar = _calendar(client, calendar_id)
        events = calendar.search(start=first, end=last, event=True, expand=True)
        return [_event_info(event, calendar_id) for event in events]


@mcp.tool()
def get_event(calendar_id: str, uid: str) -> dict[str, Any]:
    """Read one event by UID. Recurrence exceptions are included as raw iCalendar data."""
    with _client() as client:
        event = _calendar(client, calendar_id).get_event_by_uid(uid)
        result = _event_info(event, calendar_id)
        result["icalendar"] = event.data
        return result


@mcp.tool()
def create_event(calendar_id: str, title: str, start: str, end: str,
                 description: str = "", location: str = "") -> dict[str, Any]:
    """Create an event. Timed values need ISO 8601 offsets; dates create an all-day event."""
    first, last = _range(start, end)
    if not title.strip():
        raise ValueError("Title cannot be empty.")
    with _client() as client:
        calendar = _calendar(client, calendar_id)
        event = calendar.add_event(dtstart=first, dtend=last, summary=title,
                                   description=description, location=location,
                                   uid=str(uuid4()))
        backup = _backup(event, "after_create")
        return {**_event_info(event, calendar_id), "backup": backup}


@mcp.tool()
def update_event(calendar_id: str, uid: str, title: str | None = None,
                 start: str | None = None, end: str | None = None,
                 description: str | None = None,
                 location: str | None = None) -> dict[str, Any]:
    """Update the master event (whole series for recurring events). Back up full ICS before and after."""
    if all(value is None for value in (title, start, end, description, location)):
        raise ValueError("Provide at least one field to update.")
    with _client() as client:
        event = _calendar(client, calendar_id).get_event_by_uid(uid)
        current = _component(event)
        old_start = _as_iso(current.get("DTSTART"))
        old_end = _as_iso(current.get("DTEND"))
        new_start, new_end = _range(start or old_start, end or old_end)
        if title is not None and not title.strip():
            raise ValueError("Title cannot be empty.")
        before = _backup(event, "before_update")
        with event.edit_icalendar_instance() as instance:
            master = next((item for item in instance.walk() if item.name == "VEVENT" and "RECURRENCE-ID" not in item), None)
            if master is None:
                raise ValueError("Main VEVENT component not found.")
            if title is not None:
                master["SUMMARY"] = title
            if start is not None:
                master.pop("DTSTART", None)
                master.add("DTSTART", new_start)
            if end is not None:
                master.pop("DTEND", None)
                master.add("DTEND", new_end)
            if description is not None:
                master["DESCRIPTION"] = description
            if location is not None:
                master["LOCATION"] = location
        event.save()
        after = _backup(event, "after_update")
        return {**_event_info(event, calendar_id), "backup_before": before,
                "backup_after": after}


@mcp.tool()
def delete_event(calendar_id: str, uid: str) -> dict[str, str]:
    """Delete an event or recurring series after saving its full ICS backup."""
    with _client() as client:
        event = _calendar(client, calendar_id).get_event_by_uid(uid)
        backup = _backup(event, "before_delete")
        event.delete()
        return {"deleted_uid": uid, "calendar_id": calendar_id, "backup": backup}


if __name__ == "__main__":
    mcp.run(transport="stdio")
