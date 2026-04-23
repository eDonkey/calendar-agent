"""
agent.py
Agente CrewAI para gestionar Google Calendar.
"""
import os
import asyncio
import logging

from crewai import Agent, Task, Crew, Process
from google_calendar_tool import get_all_tools

logger = logging.getLogger(__name__)


async def run_calendar_agent(user_message: str) -> str:
    """Ejecuta el agente con el mensaje del usuario y retorna la respuesta."""

    # Verificar configuración mínima
    missing = [v for v in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "ANTHROPIC_API_KEY"] if not os.getenv(v)]
    if missing:
        return (
            f"⚠️ Faltan variables de entorno: {', '.join(missing)}\n\n"
            "Seguí el README para obtener tus credenciales de Google y configurarlas en Heroku."
        )

    tools = get_all_tools()

    agent = Agent(
        role="Asistente personal de Google Calendar",
        goal=(
            "Gestionar el Google Calendar del usuario: crear, leer, editar y eliminar eventos. "
            "Siempre confirmás las acciones con detalles claros y organizás los eventos cronológicamente."
        ),
        backstory=(
            "Sos un asistente personal altamente organizado, experto en gestión de agendas. "
            "Tenés acceso directo a Google Calendar. "
            "Respondés siempre en español rioplatense, de forma amigable y precisa. "
            "Cuando listás eventos los organizás por fecha. "
            "Cuando el usuario pide eliminar algo, primero buscás el evento para confirmar el ID correcto. "
            "El timezone de Argentina es UTC-3 (America/Argentina/Buenos_Aires)."
        ),
        tools=tools,
        llm="anthropic/claude-sonnet-4-20250514",
        verbose=True,
        memory=False,
        max_iter=8,
    )

    task = Task(
        description=(
            f"El usuario solicita lo siguiente:\n\n{user_message}\n\n"
            "Usá las herramientas disponibles para realizar la acción. "
            "Respondé en español rioplatense con los detalles del resultado. "
            "Si es un listado, organizalo cronológicamente. "
            "Si creaste/editaste/eliminaste algo, confirmá todos los detalles."
        ),
        agent=agent,
        expected_output=(
            "Respuesta en español sobre la acción realizada, con títulos, fechas y horas donde corresponda."
        ),
    )

    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, crew.kickoff)
    return str(result)
