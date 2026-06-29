import asyncio
import base64
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.gemini_live import GeminiLive

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO)
logging.getLogger("app.gemini_live").setLevel(logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("MODEL", "gemini-3.1-flash-live-preview")
VOICE = os.getenv("VOICE", "Puck")
SUPPORTED_MODELS = {
    "gemini-3.1-flash-live-preview": "Gemini 3.1 Flash Live Preview",
    "gemini-2.5-flash-native-audio-preview-12-2025": "Gemini 2.5 Flash Live Preview",
}
SUPPORTED_VOICES = {
    "Puck": "Puck",
    "Kore": "Kore",
    "Charon": "Charon",
    "Aoede": "Aoede",
    "Fenrir": "Fenrir",
    "Leda": "Leda",
}

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_APP_HOST = os.getenv("TWILIO_APP_HOST")
FEEDBACK_STORE = BASE_DIR / os.getenv("FEEDBACK_STORE", "data/feedback.jsonl")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class FeedbackSubmission(BaseModel):
    message: str = Field(min_length=3, max_length=2000)
    name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    rating: int | None = Field(default=None, ge=1, le=5)
    page: str | None = Field(default=None, max_length=200)


@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/feedback")
async def submit_feedback(payload: FeedbackSubmission, request: Request):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Feedback message is required")

    record = {
        "timestamp": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "message": message,
        "name": payload.name.strip() if payload.name else None,
        "email": payload.email.strip() if payload.email else None,
        "rating": payload.rating,
        "page": payload.page.strip() if payload.page else None,
        "user_agent": request.headers.get("user-agent"),
    }

    FEEDBACK_STORE.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_STORE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, model: str | None = None, voice: str | None = None
):
    await websocket.accept()

    logger.info("WebSocket connection accepted")
    selected_model = model or MODEL
    selected_voice = voice or VOICE

    if selected_model not in SUPPORTED_MODELS:
        logger.warning(f"Unsupported Gemini Live model requested: {selected_model}")
        await websocket.send_json(
            {
                "type": "error",
                "error": f"Unsupported model '{selected_model}'. Select one of the available Gemini Live models.",
            }
        )
        await websocket.close(code=1008, reason="Unsupported Gemini Live model")
        return

    if selected_voice not in SUPPORTED_VOICES:
        logger.warning(f"Unsupported Gemini Live voice requested: {selected_voice}")
        await websocket.send_json(
            {
                "type": "error",
                "error": f"Unsupported voice '{selected_voice}'. Select one of the available voices.",
            }
        )
        await websocket.close(code=1008, reason="Unsupported Gemini Live voice")
        return

    if not GEMINI_API_KEY:
        logger.error("Missing GEMINI_API_KEY; refusing Gemini Live session")
        await websocket.send_json(
            {
                "type": "error",
                "error": "Server is missing GEMINI_API_KEY. Set it in .env and restart the app.",
            }
        )
        await websocket.close(code=1011, reason="Missing GEMINI_API_KEY")
        return

    audio_input_queue = asyncio.Queue()
    video_input_queue = asyncio.Queue()
    text_input_queue = asyncio.Queue()

    async def audio_output_callback(data):
        await websocket.send_bytes(data)

    async def audio_interrupt_callback():
        pass

    gemini_client = GeminiLive(
        api_key=GEMINI_API_KEY,
        model=selected_model,
        input_sample_rate=16000,
        voice_name=selected_voice,
    )
    logger.info(
        f"Starting Gemini Live browser session with model={selected_model}, voice={selected_voice}"
    )

    async def receive_from_client():
        try:
            while True:
                message = await websocket.receive()

                if message.get("bytes"):
                    await audio_input_queue.put(message["bytes"])
                elif message.get("text"):
                    text = message["text"]
                    try:
                        payload = json.loads(text)
                        if isinstance(payload, dict) and payload.get("type") == "image":
                            logger.info(
                                f"Received image chunk from client: {len(payload['data'])} base64 chars"
                            )
                            image_data = base64.b64decode(payload["data"])
                            await video_input_queue.put(image_data)
                            continue
                    except json.JSONDecodeError:
                        pass

                    await text_input_queue.put(text)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as exc:
            logger.error(f"Error receiving from client: {exc}")

    receive_task = asyncio.create_task(receive_from_client())

    async def run_session():
        async for event in gemini_client.start_session(
            audio_input_queue=audio_input_queue,
            video_input_queue=video_input_queue,
            text_input_queue=text_input_queue,
            audio_output_callback=audio_output_callback,
            audio_interrupt_callback=audio_interrupt_callback,
        ):
            if event:
                await websocket.send_json(event)

    try:
        await run_session()
    except Exception as exc:
        import traceback

        logger.error(
            f"Error in Gemini session: {type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        )
    finally:
        receive_task.cancel()
        try:
            await websocket.close()
        except Exception:
            pass


@app.post("/twilio/inbound")
async def twilio_inbound():
    host = TWILIO_APP_HOST or "localhost:8000"
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Connecting to Gemini Live.</Say>
    <Connect>
        <Stream url="wss://{host}/twilio/stream" />
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@app.post("/twilio/outbound")
async def twilio_outbound(
    to_number: str = Query(..., description="Destination phone number (E.164 format)"),
    from_number: str = Query(
        ..., description="Your Twilio phone number (E.164 format)"
    ),
):
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return {
            "error": "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in environment"
        }
    if not TWILIO_APP_HOST:
        return {"error": "TWILIO_APP_HOST must be set in environment"}

    from twilio.rest import Client as TwilioClient

    client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    twiml = f"""<Response>
    <Say>Connecting to Gemini Live.</Say>
    <Connect>
        <Stream url="wss://{TWILIO_APP_HOST}/twilio/stream" />
    </Connect>
</Response>"""

    call = client.calls.create(
        to=to_number,
        from_=from_number,
        twiml=twiml,
    )
    logger.info(f"Outbound call initiated: {call.sid}")
    return {"callSid": call.sid, "status": call.status}


@app.websocket("/twilio/stream")
async def twilio_stream(websocket: WebSocket):
    from app.twilio_handler import TwilioHandler

    await websocket.accept()
    logger.info("Twilio media stream WebSocket connected")

    handler = TwilioHandler(gemini_api_key=GEMINI_API_KEY, model=MODEL)
    try:
        await handler.handle_media_stream(websocket)
    except Exception as exc:
        logger.error(f"Twilio stream error: {exc}", exc_info=True)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("Twilio media stream WebSocket closed")
