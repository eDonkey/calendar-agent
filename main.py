import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
