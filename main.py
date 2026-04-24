import os
import logging
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from dotenv import load_dotenv

from agent import run_calendar_agent

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Calendar Agent API iniciando...")
    yield


app = FastAPI(title="Google Calendar AI Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = []


class ChatResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(path, encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        history_text = ""
        for msg in (request.history or [])[-6:]:
            label = "Usuario" if msg.role == "user" else "Asistente"
            history_text += f"{label}: {msg.content}\n"

        full_input = request.message
        if history_text:
            full_input = f"Contexto previo:\n{history_text}\nSolicitud actual: {request.message}"

        result = await run_calendar_agent(full_input)
        return ChatResponse(response=result, success=True)

    except Exception as e:
        logger.error(f"Error: {e}")
        return ChatResponse(response="", success=False, error=str(e))


@app.get("/api/health")
async def health():
    keys = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN", "ANTHROPIC_API_KEY"]
    return {
        "status": "ok",
        "configured": {k: bool(os.getenv(k)) for k in keys}
    }


# ── Kapso / WhatsApp Webhook ─────────────────────────────────────────────────

async def send_whatsapp_reply(phone_number_id: str, to: str, text: str):
    """Envía una respuesta de texto por WhatsApp vía Kapso API."""
    kapso_key = os.getenv("KAPSO_API_KEY")
    if not kapso_key:
        logger.error("KAPSO_API_KEY no configurada.")
        return

    url = f"https://api.kapso.ai/meta/whatsapp/v24.0/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": text[:4000]},
    }
    headers = {"X-API-Key": kapso_key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code not in (200, 201):
            logger.error(f"Error enviando WhatsApp: {resp.status_code} {resp.text}")
        else:
            logger.info(f"Respuesta enviada a {to}")


async def process_whatsapp_message(phone_number_id: str, from_number: str, text: str):
    """Corre el agente y responde por WhatsApp en background."""
    try:
        logger.info(f"Procesando mensaje de {from_number}: {text[:80]}")
        result = await run_calendar_agent(text)
        await send_whatsapp_reply(phone_number_id, from_number, result)
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        await send_whatsapp_reply(
            phone_number_id, from_number,
            "Ocurrió un error. Intentá de nuevo en unos segundos."
        )


@app.post("/webhook/kapso")
async def kapso_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook que recibe mensajes de WhatsApp desde Kapso.

    Payload real de Kapso (sin envelope de evento):
    {
      "message": { "from": "...", "text": { "body": "..." }, "type": "text", ... },
      "conversation": { "phone_number_id": "...", ... },
      "phone_number_id": "..."
    }

    Configurá en Kapso:
      URL:    https://tu-app.herokuapp.com/webhook/kapso
      Evento: whatsapp.message.received
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload JSON inválido")

    logger.info(f"Webhook recibido: {str(payload)[:300]}")

    # Extraer campos del payload real de Kapso
    message = payload.get("message", {})
    msg_type = message.get("type", "")

    if msg_type != "text":
        logger.info(f"Tipo no soportado: {msg_type}")
        return JSONResponse({"status": "ignored", "reason": f"type={msg_type}"})

    text = (message.get("text") or {}).get("body", "").strip()
    from_number = message.get("from", "")

    # phone_number_id viene en la raíz o dentro de conversation
    phone_number_id = (
        payload.get("phone_number_id")
        or (payload.get("conversation") or {}).get("phone_number_id", "")
    )

    if not text or not from_number or not phone_number_id:
        logger.warning(f"Campos faltantes — from={from_number}, phone_id={phone_number_id}, text={bool(text)}")
        return JSONResponse({"status": "ignored", "reason": "missing fields"})

    # Responder 200 inmediatamente y procesar en background
    background_tasks.add_task(process_whatsapp_message, phone_number_id, from_number, text)
    return JSONResponse({"status": "accepted"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
