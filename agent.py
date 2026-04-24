"""
agent.py — Agente de Google Calendar sin CrewAI.
Usa la API de Anthropic directamente con tool_use para reducir uso de memoria
de ~600MB (CrewAI) a ~50MB.
"""
import os
import logging

import anthropic
from google_calendar_tool import (
    ListEventsTool, CreateEventTool, UpdateEventTool,
    DeleteEventTool, GetEventTool
)

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "name": "list_calendar_events",
        "description": "Lista eventos del Google Calendar. Filtrá por rango de fechas o texto libre.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_min": {"type": "string", "description": "Fecha inicio ISO8601 con timezone, ej: 2026-04-24T00:00:00-03:00"},
                "time_max": {"type": "string", "description": "Fecha fin ISO8601 con timezone"},
                "max_results": {"type": "integer", "description": "Máximo de eventos (default 10)"},
                "query": {"type": "string", "description": "Texto libre para filtrar"}
            }
        }
    },
    {
        "name": "create_calendar_event",
        "description": "Crea un nuevo evento en Google Calendar.",
        "input_schema": {
            "type": "object",
            "required": ["summary", "start", "end"],
            "properties": {
                "summary": {"type": "string"},
                "start": {"type": "string", "description": "ISO8601 con timezone -03:00"},
                "end": {"type": "string", "description": "ISO8601 con timezone -03:00"},
                "description": {"type": "string"},
                "location": {"type": "string"},
                "attendees": {"type": "array", "items": {"type": "string"}}
            }
        }
    },
    {
        "name": "update_calendar_event",
        "description": "Modifica un evento existente por su event_id.",
        "input_schema": {
            "type": "object",
            "required": ["event_id"],
            "properties": {
                "event_id": {"type": "string"},
                "summary": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "description": {"type": "string"},
                "location": {"type": "string"}
            }
        }
    },
    {
        "name": "delete_calendar_event",
        "description": "Elimina un evento por su event_id.",
        "input_schema": {
            "type": "object",
            "required": ["event_id"],
            "properties": {
                "event_id": {"type": "string"}
            }
        }
    },
    {
        "name": "get_calendar_event",
        "description": "Obtiene detalles de un evento por su ID.",
        "input_schema": {
            "type": "object",
            "required": ["event_id"],
            "properties": {
                "event_id": {"type": "string"}
            }
        }
    }
]


def execute_tool(name: str, inputs: dict) -> str:
    tools_map = {
        "list_calendar_events":  ListEventsTool(),
        "create_calendar_event": CreateEventTool(),
        "update_calendar_event": UpdateEventTool(),
        "delete_calendar_event": DeleteEventTool(),
        "get_calendar_event":    GetEventTool(),
    }
    tool = tools_map.get(name)
    if not tool:
        return f"Herramienta desconocida: {name}"
    try:
        return tool._run(**inputs)
    except Exception as e:
        logger.error(f"Error en herramienta {name}: {e}")
        return f"Error ejecutando {name}: {str(e)}"


SYSTEM_PROMPT = """Sos un asistente personal de Google Calendar.
Tenés herramientas para crear, leer, editar y eliminar eventos.

Reglas:
- Respondé en español rioplatense, amigable y conciso.
- El timezone es America/Argentina/Buenos_Aires (UTC-3). Usá siempre offset -03:00.
- Cuando listés eventos, organizalos cronológicamente.
- Antes de eliminar, confirmá el ID con list_calendar_events.
- Si no especifican hora de fin, asumí 1 hora después del inicio.
- Máximo 3-4 párrafos por respuesta.
"""


async def run_calendar_agent(user_message: str) -> str:
    """Agente con tool_use directo. ~50MB de RAM vs ~600MB de CrewAI."""
    client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = [{"role": "user", "content": user_message}]

    for _ in range(5):
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        logger.info(f"Stop reason: {response.stop_reason}")

        if response.stop_reason == "end_turn":
            return "\n".join(b.text for b in response.content if hasattr(b, "text")).strip()

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"Tool: {block.name} | Input: {block.input}")
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        break

    return "\n".join(b.text for b in response.content if hasattr(b, "text")).strip() or "No pude completar la acción."
