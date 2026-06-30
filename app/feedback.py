import json
import time

from fastapi import HTTPException, Request

from app.config import FEEDBACK_STORE
from app.schemas import FeedbackSubmission


def save_feedback(payload: FeedbackSubmission, request: Request) -> dict[str, bool]:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Feedback message is required")

    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
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
