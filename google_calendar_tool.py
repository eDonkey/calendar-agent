"""
google_calendar_tool.py — Sin dependencias de CrewAI.
Cada herramienta es una clase simple con método _run().
"""
import os
from datetime import datetime, timezone
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    if not creds.valid:
        creds.refresh(Request())
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


class ListEventsTool:
    def _run(self, time_min=None, time_max=None, max_results=10, query=None) -> str:
        service = get_calendar_service()
        now = datetime.now(timezone.utc).isoformat()
        params = {
            "calendarId": "primary",
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
            "timeMin": time_min or now,
        }
        if time_max:
            params["timeMax"] = time_max
        if query:
            params["q"] = query

        result = service.events().list(**params).execute()
        events = result.get("items", [])

        if not events:
            return "No se encontraron eventos en el período indicado."

        output = []
        for e in events:
            start = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
            end = e.get("end", {}).get("dateTime", e.get("end", {}).get("date", ""))
            attendees = [a.get("email") for a in e.get("attendees", [])]
            output.append(
                f"- ID: {e['id']}\n"
                f"  Título: {e.get('summary', 'Sin título')}\n"
                f"  Inicio: {start}\n"
                f"  Fin: {end}\n"
                f"  Descripción: {e.get('description', '-')}\n"
                f"  Ubicación: {e.get('location', '-')}\n"
                f"  Asistentes: {', '.join(attendees) if attendees else '-'}"
            )
        return "\n\n".join(output)


class CreateEventTool:
    def _run(self, summary, start, end, description=None, location=None, attendees=None) -> str:
        service = get_calendar_service()
        event = {
            "summary": summary,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
        }
        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if attendees:
            event["attendees"] = [{"email": e} for e in attendees]

        created = service.events().insert(calendarId="primary", body=event).execute()
        return (
            f"✅ Evento creado.\n"
            f"ID: {created['id']}\n"
            f"Título: {created.get('summary')}\n"
            f"Inicio: {created['start'].get('dateTime')}\n"
            f"Fin: {created['end'].get('dateTime')}\n"
            f"Link: {created.get('htmlLink')}"
        )


class UpdateEventTool:
    def _run(self, event_id, summary=None, start=None, end=None, description=None, location=None) -> str:
        service = get_calendar_service()
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        if summary:
            event["summary"] = summary
        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if start:
            event["start"]["dateTime"] = start
        if end:
            event["end"]["dateTime"] = end

        updated = service.events().update(calendarId="primary", eventId=event_id, body=event).execute()
        return (
            f"✅ Evento actualizado.\n"
            f"Título: {updated.get('summary')}\n"
            f"Inicio: {updated['start'].get('dateTime')}\n"
            f"Fin: {updated['end'].get('dateTime')}"
        )


class DeleteEventTool:
    def _run(self, event_id) -> str:
        service = get_calendar_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return f"🗑 Evento {event_id} eliminado correctamente."


class GetEventTool:
    def _run(self, event_id) -> str:
        service = get_calendar_service()
        e = service.events().get(calendarId="primary", eventId=event_id).execute()
        attendees = [a.get("email") for a in e.get("attendees", [])]
        return (
            f"ID: {e['id']}\n"
            f"Título: {e.get('summary', 'Sin título')}\n"
            f"Inicio: {e['start'].get('dateTime', e['start'].get('date'))}\n"
            f"Fin: {e['end'].get('dateTime', e['end'].get('date'))}\n"
            f"Descripción: {e.get('description', '-')}\n"
            f"Ubicación: {e.get('location', '-')}\n"
            f"Asistentes: {', '.join(attendees) if attendees else '-'}\n"
            f"Link: {e.get('htmlLink')}"
        )
