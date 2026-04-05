import re
from typing import Optional
from models.database import get_db


# ──────────────────────────────────────────────
# Keyword helpers
# ──────────────────────────────────────────────

STOP_WORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "with", "my", "i", "what", "how",
    "why", "when", "do", "does", "should", "can", "will", "would",
    "could", "please", "help", "me", "have", "has", "be", "are",
}

CATEGORY_KEYWORDS = {
    "motors": ["motor", "kv", "rpm", "stator", "bearing", "windings", "thrust"],
    "batteries": ["battery", "lipo", "mah", "4s", "6s", "3s", "voltage", "cell", "charge", "c rating"],
    "flight_controllers": ["flight controller", "fc", "betaflight", "pid", "gyro", "uart", "f4", "f7"],
    "troubleshooting": ["won't", "not working", "problem", "issue", "fix", "error", "crash", "flip", "oscillat", "vibrat"],
    "building": ["build", "solder", "frame", "tool", "assemble", "wire", "connect", "install"],
    "fpv_systems": ["fpv", "goggles", "analog", "digital", "dji", "vtx", "camera", "video", "latency"],
    "radio_receiver": ["receiver", "transmitter", "radio", "bind", "elrs", "frsky", "crossfire", "signal"],
    "safety": ["safety", "safe", "legal", "regulation", "law", "failsafe", "emergency"],
}


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 2]


def classify_category(text: str) -> Optional[str]:
    text_lower = text.lower()
    scores = {}
    for cat, kws in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in kws if kw in text_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


# ──────────────────────────────────────────────
# Database search
# ──────────────────────────────────────────────

async def search_knowledge(question: str, keywords: list[str], category: Optional[str]) -> Optional[dict]:
    """Search drone_knowledge collection using keyword matching."""
    db = get_db()
    if db is None:
        return None

    query: dict = {}
    if category:
        query["category"] = category
    if keywords:
        query["keywords"] = {"$in": keywords[:6]}

    cursor = db.drone_knowledge.find(query).limit(5)
    docs = await cursor.to_list(length=5)

    if docs:
        # Return highest-matching doc (most keyword hits)
        def score(doc):
            doc_kws = doc.get("keywords", [])
            return len(set(keywords) & set(doc_kws))

        return max(docs, key=score)

    # Fallback: search without category filter
    if category and keywords:
        cursor2 = db.drone_knowledge.find(
            {"keywords": {"$in": keywords[:4]}}
        ).limit(3)
        docs2 = await cursor2.to_list(length=3)
        if docs2:
            return docs2[0]

    return None


async def search_troubleshooting(question: str) -> Optional[dict]:
    """Search troubleshooting_cases collection."""
    db = get_db()
    if db is None:
        return None

    keywords = extract_keywords(question)
    curse = db.troubleshooting_cases.find(
        {"$or": [
            {"problem": {"$regex": "|".join(keywords[:3]), "$options": "i"}},
            {"category": {"$in": [classify_category(question)]}},
        ]}
    ).limit(3)
    docs = await curse.to_list(length=3)
    return docs[0] if docs else None


async def get_related_topics(category: Optional[str], limit: int = 3) -> list[dict]:
    """Return a few related Q&A titles for the sidebar."""
    db = get_db()
    if db is None or not category:
        return []
    cursor = db.drone_knowledge.find(
        {"category": category},
        {"question": 1, "_id": 1}
    ).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [{"title": d["question"], "id": str(d["_id"])} for d in docs]
