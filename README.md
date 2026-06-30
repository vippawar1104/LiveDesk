# Live Desk

Live Desk is a realtime multimodal web app built on the Gemini Live API, FastAPI, and vanilla JavaScript.

It provides a voice-first assistant that can:
- talk back in realtime
- accept microphone input automatically on connect
- accept typed messages
- use camera or screen-share context
- adapt to the user's language

The current app is a polished prototype with a stronger product-style frontend and a purpose-specific system prompt for a live workspace copilot.

## What It Does

Live Desk is designed for:
- live walkthroughs
- screen-share guidance
- visual Q&A
- multilingual conversations
- fast troubleshooting and brainstorming

The backend streams audio, text, and image context to Gemini Live and streams audio plus transcript events back to the browser.

## Stack

- FastAPI for the backend and WebSocket server
- Google `google-genai` Python SDK for Gemini Live
- Vanilla JavaScript frontend with no build step
- Browser APIs for microphone, camera, screen sharing, and audio playback

## Project Structure

```text
.
├── app
│   ├── config.py
│   ├── feedback.py
│   ├── server.py
│   ├── gemini_live.py
│   ├── live_session.py
│   └── schemas.py
├── main.py
├── requirements.txt
├── Dockerfile
├── deployment_cloud_run.md
└── frontend
    ├── index.html
    └── static
        ├── style.css
        ├── main.js
        ├── gemini-client.js
        ├── media-handler.js
        └── pcm-processor.js
```

## Requirements

- Python 3.11+
- A Gemini API key
- A modern browser with microphone support
- Camera/screen-share permissions if you want visual input

## Setup

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
MODEL=gemini-3.1-flash-live-preview
```

Notes:
- `GEMINI_API_KEY` is required.
- `MODEL` defaults to `gemini-3.1-flash-live-preview` if not set.

## Run The App

Start the backend:

```bash
PORT=8000 ./.venv/bin/python main.py
```

If port `8000` is already in use, use a different port:

```bash
PORT=8002 ./.venv/bin/python main.py
```

Then open:

```text
http://127.0.0.1:8000
```

Or the port you selected.

## How The UI Works

1. Click `Connect`
2. The browser immediately requests microphone access
3. Once permission is granted, the WebSocket session opens
4. You can then:
   - speak to the assistant
   - type messages
   - start camera
   - share your screen
   - disconnect at any time

Current behavior:
- microphone starts on connect
- disconnect stops queued AI audio immediately
- the assistant can continue in the user's preferred language

## System Prompt

The assistant prompt is defined in [app/gemini_live.py](./app/gemini_live.py).

It currently positions the model as `Live Desk`, a realtime multimodal workspace copilot with guardrails around:
- staying grounded in visible/shared context
- admitting uncertainty
- avoiding harmful or deceptive guidance
- avoiding sensitive inferences from people in images/audio
- staying high-level on medical, legal, and financial topics

## API Surface

### HTTP

- `GET /`
  - serves the frontend

### WebSocket

- `WS /ws`
  - primary browser session endpoint
  - receives audio bytes and text/image payloads
  - sends audio bytes and JSON transcript/session events

## Development Notes

- Static frontend assets are served directly by FastAPI under `/static`
- There is no frontend build process
- Asset URLs use version query params for cache busting
- The backend will reject a session early if `GEMINI_API_KEY` is missing

## Known Limitations

This is not fully production-ready yet. Current gaps include:
- no authentication
- no rate limiting
- minimal reconnect/session recovery
- limited observability and analytics
- broad CORS configuration
- limited server-side validation
- some disconnect-edge-case cleanup still depends on browser behavior

## Production Hardening Checklist

Before shipping this publicly, add:
- authentication and access control
- request and session limits
- structured logging and monitoring
- retries and reconnect handling
- better error taxonomy and user-facing recovery states
- environment-specific config management
- secure CORS policy
- deployment health checks
- automated tests for WebSocket and media flows

## Troubleshooting

### `No API key was provided`

Your `.env` is missing `GEMINI_API_KEY`, or the server was not restarted after updating it.

### `address already in use`

The selected port is busy. Start on another port:

```bash
PORT=8002 ./.venv/bin/python main.py
```

### `zsh: no such file or directory: ./.venv/bin/python`

You are either:
- in the wrong directory
- missing the virtual environment

Fix:

```bash
cd gemini-live-genai-python-sdk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Browser connects but nothing happens

Refresh the page once so the latest static assets load, especially after frontend changes.

## License / Usage

This repository is currently structured as an example application. Add your own license and deployment policies before distributing it publicly.
