import asyncio
import base64
import json
import logging
from contextlib import suppress

from fastapi import WebSocket, WebSocketDisconnect

from app.config import GEMINI_API_KEY, MODEL, SUPPORTED_MODELS, SUPPORTED_VOICES, VOICE
from app.gemini_live import GeminiLive

logger = logging.getLogger(__name__)
logging.getLogger("app.gemini_live").setLevel(logging.DEBUG)


async def run_browser_session(
    websocket: WebSocket, model: str | None = None, voice: str | None = None
) -> None:
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

    audio_input_queue: asyncio.Queue[bytes] = asyncio.Queue()
    video_input_queue: asyncio.Queue[bytes] = asyncio.Queue()
    text_input_queue: asyncio.Queue[str] = asyncio.Queue()

    async def audio_output_callback(data: bytes) -> None:
        await websocket.send_bytes(data)

    async def audio_interrupt_callback() -> None:
        return None

    gemini_client = GeminiLive(
        api_key=GEMINI_API_KEY,
        model=selected_model,
        input_sample_rate=16000,
        voice_name=selected_voice,
    )
    logger.info(
        f"Starting Gemini Live browser session with model={selected_model}, voice={selected_voice}"
    )

    async def receive_from_client() -> None:
        try:
            while True:
                message = await websocket.receive()

                if message.get("bytes"):
                    await audio_input_queue.put(message["bytes"])
                    continue

                text = message.get("text")
                if not text:
                    continue

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

    try:
        async for event in gemini_client.start_session(
            audio_input_queue=audio_input_queue,
            video_input_queue=video_input_queue,
            text_input_queue=text_input_queue,
            audio_output_callback=audio_output_callback,
            audio_interrupt_callback=audio_interrupt_callback,
        ):
            if event:
                await websocket.send_json(event)
    except Exception as exc:
        import traceback

        logger.error(
            f"Error in Gemini session: {type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        )
    finally:
        receive_task.cancel()
        with suppress(asyncio.CancelledError):
            await receive_task
        with suppress(Exception):
            await websocket.close()
