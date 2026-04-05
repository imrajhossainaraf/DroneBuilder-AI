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
    search_components_for_chat,
    get_related_topics,
    format_troubleshooting_context,
    format_component_context,
)
from services.ai_handler import get_ai_response, build_prompt, check_ollama_status, provider_flags
from utils.helpers import mongo_doc_to_dict

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
        "version": "2.0.0",
        "database": "connected" if db_ok else "disconnected",
        "ollama": ollama,
        **provider_flags(),
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
    db = get_db()

    # ── Step 1: Understand the question ──
    keywords = extract_keywords(question)
    category = classify_category(question)

    # ── Step 2: Load conversation history for context ──
    conversation_history = []
    if db is not None:
        conv = await db.conversations.find_one({"session_id": session_id})
        if conv:
            conversation_history = conv.get("messages", [])[-6:]  # last 3 turns

    # ── Step 3: Search knowledge base ──
    db_result = await search_knowledge(question, keywords, category)

    # If general knowledge didn't match, try troubleshooting DB
    trouble_result = None
    is_troubleshooting = any(
        w in question.lower()
        for w in ["won't", "not", "problem", "fix", "error", "crash", "help",
                  "issue", "broken", "fail", "beep", "flip", "drift", "oscillat"]
    ) or category == "troubleshooting"

    if is_troubleshooting:
        trouble_result = await search_troubleshooting(question)
        # Use troubleshooting result if it scores better, or as supplement
        if not db_result and trouble_result:
            db_result = trouble_result

    # ── Step 4: Search for relevant components ──
    component_docs = await search_components_for_chat(category, keywords, limit=3)
    component_context = format_component_context(component_docs) if component_docs else None

    # Format component docs for API response (strip _id, keep useful fields)
    relevant_components = []
    for cdoc in component_docs:
        clean = mongo_doc_to_dict(cdoc)
        relevant_components.append({
            "id": clean.get("id"),
            "name": clean.get("name"),
            "brand": clean.get("brand"),
            "component_type": clean.get("component_type"),
            "specs": clean.get("specs", {}),
            "price_range": clean.get("price_range"),
            "use_cases": clean.get("use_cases", []),
            "pros": clean.get("pros", []),
            "cons": clean.get("cons", []),
            "rating": clean.get("rating", 0),
        })

    # ── Step 5: Build AI context from DB results ──
    db_context = None
    if trouble_result and trouble_result == db_result:
        # Use structured troubleshooting format
        db_context = format_troubleshooting_context(trouble_result)
    elif db_result:
        answer = db_result.get("answer", "")
        db_context = answer if answer else None

    # ── Step 6: Build the prompt and call AI ──
    from datetime import datetime
    prompt = build_prompt(
        question=question,
        db_context=db_context,
        category=category or "",
        conversation_history=conversation_history,
        component_context=component_context,
        user_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    ai_text, model_used = await get_ai_response(
        prompt,
        provider=req.ai_provider,
        response_detail=req.response_detail,
    )

    # ── Step 7: Determine source and confidence ──
    if db_result and model_used != "none":
        source = "database_enhanced"
        confidence = 0.95
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

    # ── Step 8: Related topics for sidebar ──
    related = await get_related_topics(category, limit=3)

    # ── Step 9: Save conversation to DB ──
    if db is not None:
        await db.conversations.update_one(
            {"session_id": session_id},
            {
                "$push": {
                    "messages": {
                        "$each": [
                            {
                                "role": "user",
                                "content": question,
                                "timestamp": datetime.now(timezone.utc),
                            },
                            {
                                "role": "assistant",
                                "content": ai_text,
                                "source": source,
                                "ai_model": model_used,
                                "category": category,
                                "timestamp": datetime.now(timezone.utc),
                            },
                        ]
                    }
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
        relevant_components=relevant_components,
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
    for m in msgs:
        if "timestamp" in m and hasattr(m["timestamp"], "isoformat"):
            m["timestamp"] = m["timestamp"].isoformat()
    return {"messages": msgs, "session_id": session_id}


# ──────────────────────────────────────────────
# Suggested questions helper
# ──────────────────────────────────────────────

_SUGGESTIONS = {
    "motors": [
        "What KV motor is best for 5-inch freestyle on 6S?",
        "How do I reverse motor direction in Betaflight?",
        "What causes a motor to overheat after 2 minutes?",
    ],
    "batteries": [
        "What is the difference between 4S and 6S LiPo?",
        "How do I store LiPo batteries safely?",
        "What C rating do I need for a 5-inch quad?",
    ],
    "flight_controllers": [
        "How do I flash Betaflight firmware step by step?",
        "How do I start PID tuning as a beginner?",
        "F4 vs F7 flight controller — which should I buy?",
    ],
    "troubleshooting": [
        "My drone flips on takeoff — what is wrong?",
        "Why is my ESC beeping continuously after arming?",
        "How do I fix FPV video static and interference?",
    ],
    "building": [
        "What tools do I need to build my first drone?",
        "How do I solder an XT60 connector safely?",
        "What is a smoke stopper and should I use one?",
    ],
    "fpv_systems": [
        "What is the difference between analog and digital FPV?",
        "What VTX power output is legal in my country?",
        "DJI O3 vs Walksnail Avatar — which is better?",
    ],
    "radio_receiver": [
        "How do I bind my ELRS receiver to my transmitter?",
        "What is ELRS and why is it popular?",
        "How do I configure failsafe in Betaflight?",
    ],
    "safety": [
        "What are the basic safety rules for FPV drones?",
        "Do I need to register my drone with the FAA?",
        "How do I configure a proper failsafe?",
    ],
    "esc": [
        "What is the difference between BLHeli_32 and AM32?",
        "How do I calibrate my ESCs?",
        "What DSHOT protocol should I use?",
    ],
    "props": [
        "What props should I use for 5-inch freestyle?",
        "Tri-blade vs bi-blade props — which is better?",
        "How do I balance my propellers?",
    ],
    "gps": [
        "How do I set up GPS rescue in Betaflight?",
        "Why won't my GPS get a satellite fix?",
        "Which GPS module is best for long range?",
    ],
}

_DEFAULT_SUGGESTIONS = [
    "What motor should I use for a 5-inch racing drone?",
    "My drone won't arm — what should I check first?",
    "Recommend a beginner-friendly 5-inch build under $300",
]


def _suggest_questions(category: str | None) -> list[str]:
    return _SUGGESTIONS.get(category or "", _DEFAULT_SUGGESTIONS)[:3]
