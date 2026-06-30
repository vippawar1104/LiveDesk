import asyncio
import inspect
import logging
import traceback

logger = logging.getLogger(__name__)
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types

SYSTEM_PROMPT = """
You are Live Desk, a real-time voice tutor for students.

Primary role:
- Help the user understand concepts clearly, quickly, and safely through spoken conversation.
- Optimize for fast, natural, low-friction voice interaction.
- Keep answers short by default and expand only when the user asks for more detail.

Core behavior:
- Respond immediately in a calm, direct, voice-friendly style.
- Use short sentences and natural spoken wording.
- Start with the answer instead of a long preamble.
- For simple questions, answer in 1 to 3 short sentences.
- For explanation requests, give a compact step-by-step explanation.
- If the user interrupts, stop the current line of reasoning and respond to the latest request.
- If the request is unclear, ask one short clarifying question.
- When the user shares visual context, ground your answer in what is actually visible.
- Never pretend to have clicked, opened, changed, or verified something you did not actually observe in the session.

Language behavior:
- Match the user's language automatically.
- If the user speaks in Hindi, reply in Hindi.
- If the user speaks in Hinglish, reply in Hinglish.
- If the user speaks in English, reply in clear spoken English.
- Keep wording simple and natural for Indian users.
- When replying in Hindi or any other Indian regional language, use the native script in text and transcript output by default.
- Do not transliterate Hindi or regional-language replies into English letters unless the user explicitly asks for Romanized text.

Speech quality rules:
- Do not stutter.
- Do not repeat words, phrases, or the user's question unless necessary.
- Do not self-correct aloud or restart sentences.
- Do not use filler such as "um", "uh", "let me think", or similar hesitation phrases.
- Do not ramble.
- End cleanly without trailing filler.

Teaching behavior:
- Explain concepts clearly and accurately.
- Help the student learn the method, not just copy answers blindly.
- Break difficult topics into small understandable parts.
- Use examples only when they improve understanding.
- Prefer concise explanations that sound natural when spoken aloud.
- When the user asks about visible content on a camera feed or shared screen, explain it clearly and in a logical order.

Camera and screen-share analysis:
- When asked what is visible, first summarize the overall scene, page, application, document, or interface, then explain the important details in a logical order.
- Describe relevant objects, controls, sections, messages, charts, code, documents, and visible text. Read important text exactly when it is clear enough to read; otherwise state that it is partially visible or unreadable.
- For interfaces and workflows, explain what each relevant visible element appears to do and provide clear step-by-step guidance when the user asks what to click or do next.
- For code, errors, dashboards, forms, and documents, explain the visible content, identify the likely issue or meaning, and suggest practical next steps based only on available evidence.
- Track changes across incoming camera or screen frames and use recent visual context, while prioritizing the latest clearly visible frame.
- Distinguish direct observations from interpretations. Use wording such as "I can see" for confirmed details and "this appears to" for reasonable but uncertain interpretations.
- Focus on details relevant to the user's question. If no specific question is given, provide a useful overview and ask which part they want explained further.
- Never claim that hidden, cropped, blurred, too small, or off-screen content is visible. Ask the user to move the camera, zoom in, scroll, or share the relevant area when necessary.

Safety and refusal behavior:
- Be helpful, but do not provide explicit sexual content.
- Do not provide erotic, pornographic, graphic sexual, or sexually stimulating details.
- Do not provide sexually explicit roleplay or sexual content involving minors.
- If the user asks for explicit sexual content, refuse briefly and offer a safe non-explicit alternative.
- Do not provide instructions for harm, violence, self-harm, fraud, scams, credential theft, malware, or illegal evasion.
- Do not give dishonest exam cheating assistance. If the user asks for cheating help or only the final answer in an exam context, refuse briefly and offer a learning-oriented explanation instead.
- For medical, legal, or financial topics, stay high level, avoid definitive claims, and suggest a qualified professional when appropriate.

Refusal style:
- Refuse in one short sentence.
- Then offer one safe alternative.
- Do not lecture.

Response optimization:
- Assume this is a live voice conversation.
- Keep the first response chunk short and meaningful.
- Answer in the fewest words that still solve the user's request.
- Do not think aloud.
- Do not restate the question unless needed for clarity.
- Do not add unnecessary context unless the user asks for it.

Identity:
- If asked about who your developer is or who created or developed you, say that Vipul is your developer and that he developed LiveDesk.
""".strip()


class GeminiLive:
    """
    Handles the interaction with the Gemini Live API.
    """

    def __init__(
        self,
        api_key,
        model,
        input_sample_rate,
        voice_name="Puck",
        tools=None,
        tool_mapping=None,
    ):
        """
        Initializes the GeminiLive client.

        Args:
            api_key (str): The Gemini API Key.
            model (str): The model name to use.
            input_sample_rate (int): The sample rate for audio input.
            tools (list, optional): List of tools to enable. Defaults to None.
            tool_mapping (dict, optional): Mapping of tool names to functions. Defaults to None.
        """
        self.api_key = api_key
        self.model = model
        self.input_sample_rate = input_sample_rate
        self.voice_name = voice_name
        self.client = genai.Client(api_key=api_key)
        self.tools = tools or []
        self.tool_mapping = tool_mapping or {}

    async def start_session(
        self,
        audio_input_queue,
        video_input_queue,
        text_input_queue,
        audio_output_callback,
        audio_interrupt_callback=None,
    ):
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
            system_instruction=types.Content(parts=[types.Part(text=SYSTEM_PROMPT)]),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                turn_coverage="TURN_INCLUDES_ONLY_ACTIVITY",
            ),
            tools=self.tools,
        )

        logger.info(
            f"Connecting to Gemini Live with model={self.model}, voice={self.voice_name}"
        )
        try:
            async with self.client.aio.live.connect(
                model=self.model, config=config
            ) as session:
                logger.info("Gemini Live session opened successfully")

                async def send_audio():
                    try:
                        while True:
                            chunk = await audio_input_queue.get()
                            await session.send_realtime_input(
                                audio=types.Blob(
                                    data=chunk,
                                    mime_type=f"audio/pcm;rate={self.input_sample_rate}",
                                )
                            )
                    except asyncio.CancelledError:
                        logger.debug("send_audio task cancelled")
                    except Exception as e:
                        logger.error(f"send_audio error: {e}\n{traceback.format_exc()}")

                async def send_video():
                    try:
                        while True:
                            chunk = await video_input_queue.get()
                            logger.info(
                                f"Sending video frame to Gemini: {len(chunk)} bytes"
                            )
                            await session.send_realtime_input(
                                video=types.Blob(data=chunk, mime_type="image/jpeg")
                            )
                    except asyncio.CancelledError:
                        logger.debug("send_video task cancelled")
                    except Exception as e:
                        logger.error(f"send_video error: {e}\n{traceback.format_exc()}")

                async def send_text():
                    try:
                        while True:
                            text = await text_input_queue.get()
                            logger.info(f"Sending text to Gemini: {text}")
                            await session.send_realtime_input(text=text)
                    except asyncio.CancelledError:
                        logger.debug("send_text task cancelled")
                    except Exception as e:
                        logger.error(f"send_text error: {e}\n{traceback.format_exc()}")

                event_queue = asyncio.Queue()

                async def receive_loop():
                    try:
                        while True:
                            async for response in session.receive():
                                logger.debug(
                                    f"Received response from Gemini: {response}"
                                )

                                # Log the raw response type for debugging
                                if response.go_away:
                                    logger.warning(
                                        f"Received GoAway from Gemini: {response.go_away}"
                                    )
                                if response.session_resumption_update:
                                    logger.info(
                                        f"Session resumption update: {response.session_resumption_update}"
                                    )

                                server_content = response.server_content
                                tool_call = response.tool_call

                                if server_content:
                                    if server_content.model_turn:
                                        for part in server_content.model_turn.parts:
                                            if part.inline_data:
                                                if inspect.iscoroutinefunction(
                                                    audio_output_callback
                                                ):
                                                    await audio_output_callback(
                                                        part.inline_data.data
                                                    )
                                                else:
                                                    audio_output_callback(
                                                        part.inline_data.data
                                                    )

                                    if (
                                        server_content.input_transcription
                                        and server_content.input_transcription.text
                                    ):
                                        await event_queue.put(
                                            {
                                                "type": "user",
                                                "text": server_content.input_transcription.text,
                                            }
                                        )

                                    if (
                                        server_content.output_transcription
                                        and server_content.output_transcription.text
                                    ):
                                        await event_queue.put(
                                            {
                                                "type": "gemini",
                                                "text": server_content.output_transcription.text,
                                            }
                                        )

                                    if server_content.turn_complete:
                                        await event_queue.put({"type": "turn_complete"})

                                    if server_content.interrupted:
                                        if audio_interrupt_callback:
                                            if inspect.iscoroutinefunction(
                                                audio_interrupt_callback
                                            ):
                                                await audio_interrupt_callback()
                                            else:
                                                audio_interrupt_callback()
                                        await event_queue.put({"type": "interrupted"})

                                if tool_call:
                                    function_responses = []
                                    for fc in tool_call.function_calls:
                                        func_name = fc.name
                                        args = fc.args or {}

                                        if func_name in self.tool_mapping:
                                            try:
                                                tool_func = self.tool_mapping[func_name]
                                                if inspect.iscoroutinefunction(
                                                    tool_func
                                                ):
                                                    result = await tool_func(**args)
                                                else:
                                                    loop = asyncio.get_running_loop()
                                                    result = await loop.run_in_executor(
                                                        None, lambda: tool_func(**args)
                                                    )
                                            except Exception as e:
                                                result = f"Error: {e}"

                                            function_responses.append(
                                                types.FunctionResponse(
                                                    name=func_name,
                                                    id=fc.id,
                                                    response={"result": result},
                                                )
                                            )
                                            await event_queue.put(
                                                {
                                                    "type": "tool_call",
                                                    "name": func_name,
                                                    "args": args,
                                                    "result": result,
                                                }
                                            )

                                    await session.send_tool_response(
                                        function_responses=function_responses
                                    )

                            # session.receive() iterator ended (e.g. after turn_complete) — re-enter to keep listening
                            logger.debug(
                                "Gemini receive iterator completed, re-entering receive loop"
                            )

                    except asyncio.CancelledError:
                        logger.debug("receive_loop task cancelled")
                    except Exception as e:
                        logger.error(
                            f"receive_loop error: {type(e).__name__}: {e}\n{traceback.format_exc()}"
                        )
                        await event_queue.put(
                            {"type": "error", "error": f"{type(e).__name__}: {e}"}
                        )
                    finally:
                        logger.info("receive_loop exiting")
                        await event_queue.put(None)

                send_audio_task = asyncio.create_task(send_audio())
                send_video_task = asyncio.create_task(send_video())
                send_text_task = asyncio.create_task(send_text())
                receive_task = asyncio.create_task(receive_loop())

                try:
                    while True:
                        event = await event_queue.get()
                        if event is None:
                            break
                        if isinstance(event, dict) and event.get("type") == "error":
                            # Just yield the error event, don't raise to keep the stream alive if possible or let caller handle
                            yield event
                            break
                        yield event
                finally:
                    logger.info("Cleaning up Gemini Live session tasks")
                    send_audio_task.cancel()
                    send_video_task.cancel()
                    send_text_task.cancel()
                    receive_task.cancel()
        except Exception as e:
            logger.error(
                f"Gemini Live session error: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            )
            raise
        finally:
            logger.info("Gemini Live session closed")
