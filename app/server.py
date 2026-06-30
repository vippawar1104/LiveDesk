import logging

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_DIR, STATIC_DIR
from app.feedback import save_feedback
from app.live_session import run_browser_session
from app.schemas import FeedbackSubmission

logging.getLogger("app.gemini_live").setLevel(logging.DEBUG)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/feedback")
async def submit_feedback(payload: FeedbackSubmission, request: Request):
    return save_feedback(payload, request)


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, model: str | None = None, voice: str | None = None
):
    await run_browser_session(websocket, model=model, voice=voice)
