import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse, FeedbackRequest
from models.database import get_db
from services.search_engine import (
    extract_keywords,
    classify_category,
    search_knowledge,
    search_troubleshooting,
    get_related_topics,
)
from services.ai_handler import get_ai_response, build_prompt, check_ollama_status

router = APIRouter(prefix="/api", tags=["chat"])


# ──────────────────────────────────────────────
# Health / Status
# ──────────────────────────────────────────────

@router.get("/status")
async def status():
    ollama = check_ollama_status()
    db = get_db()
    db_ok = db is not None
    return {
        "app": "DroneMate",
        "version": "1.0.0",
        "database": "connected" if db_ok else "disconnected",
        "ollama": ollama,
    }


# ──────────────────────────────────────────────
# Main Chat Endpoint
# ──────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    session_id = req.session_id or str(uuid.uuid4())

    # 1. Understand the question
    keywords = extract_keywords(question)
    category = classify_category(question)

    # 2. Search database
    db_result = await search_knowledge(question, keywords, category)

    # If no general knowledge, try troubleshooting collection
    if not db_result and any(
        w in question.lower() for w in ["won't", "not", "problem", "fix", "error", "crash", "help"]
    ):
        db_result = await search_troubleshooting(question)

    # 3. Build prompt
    db_context = None
    if db_result:
        db_context = db_result.get("answer") or db_result.get("possible_causes", "")
        if isinstance(db_context, list):
            db_context = "\n".join(
                f"- {c.get('cause', '')}: {c.get('solution', '')}"
                for c in db_context
            )

    prompt = build_prompt(question, db_context, category or "")

    # 4. Get AI response
    ai_text, model_used = get_ai_response(prompt)

    # 5. Determine source label
    if db_result and model_used != "none":
        source = "database_enhanced"
        confidence = 0.92
    elif db_result:
        source = "database"
        ai_text = db_context or ai_text
        confidence = 0.85
    elif model_used != "none":
        source = "ai"
        confidence = 0.75
    else:
        source = "error"
        confidence = 0.0

    # 6. Related topics
    related = await get_related_topics(category, limit=3)

    # 7. Save conversation to DB
    db = get_db()
    if db is not None:
        await db.conversations.update_one(
            {"session_id": session_id},
            {
                "$push": {
                    "messages": [
                        {"role": "user", "content": question, "timestamp": datetime.now(timezone.utc)},
                        {
                            "role": "assistant",
                            "content": ai_text,
                            "source": source,
                            "ai_model": model_used,
                            "timestamp": datetime.now(timezone.utc),
                        },
                    ]
                },
                "$setOnInsert": {"started_at": datetime.now(timezone.utc)},
                "$set": {"last_updated": datetime.now(timezone.utc)},
            },
            upsert=True,
        )

    return ChatResponse(
        response=ai_text,
        source=source,
        ai_model=model_used,
        confidence=confidence,
        related_topics=related,
        suggested_questions=_suggest_questions(category),
        session_id=session_id,
    )


# ──────────────────────────────────────────────
# Feedback Endpoint
# ──────────────────────────────────────────────

@router.post("/feedback")
async def feedback(req: FeedbackRequest):
    db = get_db()
    if db is not None:
        await db.user_feedback.insert_one({
            "conversation_id": req.conversation_id,
            "question": req.question,
            "answer_provided": req.answer_provided,
            "was_helpful": req.was_helpful,
            "feedback_text": req.feedback_text,
            "timestamp": datetime.now(timezone.utc),
        })
    return {"status": "ok", "message": "Thank you for your feedback!"}


# ──────────────────────────────────────────────
# History Endpoint
# ──────────────────────────────────────────────

@router.get("/history/{session_id}")
async def history(session_id: str):
    db = get_db()
    if db is None:
        return {"messages": []}
    conv = await db.conversations.find_one({"session_id": session_id})
    if not conv:
        return {"messages": []}
    msgs = conv.get("messages", [])
    # Convert ObjectId / datetime for JSON serialisation
    for m in msgs:
        if "timestamp" in m and hasattr(m["timestamp"], "isoformat"):
            m["timestamp"] = m["timestamp"].isoformat()
    return {"messages": msgs, "session_id": session_id}


# ──────────────────────────────────────────────
# Suggested questions helper
# ──────────────────────────────────────────────

_SUGGESTIONS = {
    "motors": [
        "What KV motor is best for 5-inch freestyle?",
        "How do I reverse motor direction?",
        "What causes a motor to overheat?",
    ],
    "batteries": [
        "What is the difference between 4S and 6S?",
        "How do I store LiPo batteries safely?",
        "What C rating do I need?",
    ],
    "flight_controllers": [
        "How do I flash Betaflight firmware?",
        "What is PID tuning?",
        "F4 vs F7 flight controller — which is better?",
    ],
    "troubleshooting": [
        "My drone flips on takeoff — what is wrong?",
        "Why is my ESC beeping continuously?",
        "How do I fix FPV video static?",
    ],
    "building": [
        "What tools do I need to build a drone?",
        "How do I solder an XT60 connector?",
        "What is a smoke stopper?",
    ],
    "fpv_systems": [
        "What is the difference between analog and digital FPV?",
        "What VTX power output should I use?",
    ],
    "radio_receiver": [
        "How do I bind my receiver to my transmitter?",
        "What is ELRS and why is it popular?",
    ],
    "safety": [
        "What are the basic safety rules for FPV drones?",
        "How do I configure failsafe?",
    ],
}

_DEFAULT_SUGGESTIONS = [
    "What motor should I use for a 5-inch racing drone?",
    "My drone won't arm — what should I check?",
    "Recommend a beginner-friendly build under $300",
]


def _suggest_questions(category: str | None) -> list[str]:
    return _SUGGESTIONS.get(category, _DEFAULT_SUGGESTIONS)[:3]
