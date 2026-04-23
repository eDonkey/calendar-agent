"""
google_calendar_tool.py
Wrapper de Google Calendar API como herramienta de CrewAI.
Usa OAuth2 con refresh_token almacenado en variables de entorno.
"""
import os
import json
from datetime import datetime, timezone
from typing import Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    """Construye el cliente de Google Calendar API usando variables de entorno."""
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    # Refresca automáticamente si el token expiró
    if not creds.valid:
        creds.refresh(Request())
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


# ── Inputs ──────────────────────────────────────────────────────────────────

class ListEventsInput(BaseModel):
    time_min: Optional[str] = Field(None, description="Fecha inicio ISO8601, ej: 2025-04-23T00:00:00Z")
    time_max: Optional[str] = Field(None, description="Fecha fin ISO8601, ej: 2025-04-30T23:59:59Z")
    max_results: int = Field(10, description="Máximo de eventos a retornar")
    query: Optional[str] = Field(None, description="Texto libre para filtrar eventos")


class CreateEventInput(BaseModel):
    summary: str = Field(..., description="Título del evento")
    start: str = Field(..., description="Inicio ISO8601, ej: 2025-04-24T10:00:00-03:00")
    end: str = Field(..., description="Fin ISO8601, ej: 2025-04-24T11:00:00-03:00")
    description: Optional[str] = Field(None, description="Descripción del evento")
    location: Optional[str] = Field(None, description="Ubicación del evento")
    attendees: Optional[list[str]] = Field(None, description="Lista de emails de invitados")


class UpdateEventInput(BaseModel):
    event_id: str = Field(..., description="ID del evento a modificar")
    summary: Optional[str] = Field(None, description="Nuevo título")
    start: Optional[str] = Field(None, description="Nueva fecha/hora de inicio ISO8601")
    end: Optional[str] = Field(None, description="Nueva fecha/hora de fin ISO8601")
    description: Optional[str] = Field(None, description="Nueva descripción")
    location: Optional[str] = Field(None, description="Nueva ubicación")


class DeleteEventInput(BaseModel):
    event_id: str = Field(..., description="ID del evento a eliminar")


class GetEventInput(BaseModel):
    event_id: str = Field(..., description="ID del evento a consultar")


# ── Tools ────────────────────────────────────────────────────────────────────

class ListEventsTool(BaseTool):
    name: str = "list_calendar_events"
    description: str = (
        "Lista eventos del Google Calendar del usuario. "
        "Podés filtrar por rango de fechas o texto. "
        "Retorna id, título, fechas, descripción y asistentes de cada evento."
    )
    args_schema: Type[BaseModel] = ListEventsInput

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


class CreateEventTool(BaseTool):
    name: str = "create_calendar_event"
    description: str = (
        "Crea un nuevo evento en Google Calendar. "
        "Requiere título, fecha/hora de inicio y fin en formato ISO8601 "
        "con timezone (ej: 2025-04-24T10:00:00-03:00 para Argentina). "
        "Opcionalmente acepta descripción, ubicación y lista de emails de invitados."
    )
    args_schema: Type[BaseModel] = CreateEventInput

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
            f"✅ Evento creado exitosamente.\n"
            f"ID: {created['id']}\n"
            f"Título: {created.get('summary')}\n"
            f"Inicio: {created['start'].get('dateTime')}\n"
            f"Fin: {created['end'].get('dateTime')}\n"
            f"Link: {created.get('htmlLink')}"
        )


class UpdateEventTool(BaseTool):
    name: str = "update_calendar_event"
    description: str = (
        "Modifica un evento existente en Google Calendar. "
        "Requiere el event_id. Solo actualizá los campos que cambien."
    )
    args_schema: Type[BaseModel] = UpdateEventInput

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


class DeleteEventTool(BaseTool):
    name: str = "delete_calendar_event"
    description: str = (
        "Elimina un evento de Google Calendar dado su event_id. "
        "Antes de llamar esta herramienta, confirmá el ID con list_calendar_events."
    )
    args_schema: Type[BaseModel] = DeleteEventInput

    def _run(self, event_id) -> str:
        service = get_calendar_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return f"🗑 Evento {event_id} eliminado correctamente."


class GetEventTool(BaseTool):
    name: str = "get_calendar_event"
    description: str = "Obtiene los detalles completos de un evento por su ID."
    args_schema: Type[BaseModel] = GetEventInput

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


def get_all_tools():
    return [
        ListEventsTool(),
        CreateEventTool(),
        UpdateEventTool(),
        DeleteEventTool(),
        GetEventTool(),
    ]
