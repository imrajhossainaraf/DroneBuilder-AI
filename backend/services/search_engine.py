"""
DroneMate Search Engine
- Keyword + category matching (fast, precise)
- MongoDB text search fallback (broader coverage)
- Relevance scoring across multiple signals
- Component search for chat context injection
"""
import re
from typing import Optional
from models.database import get_db


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

STOP_WORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "with", "my", "i", "what", "how",
    "why", "when", "do", "does", "should", "can", "will", "would",
    "could", "please", "help", "me", "have", "has", "be", "are",
    "this", "that", "which", "there", "get", "use", "using", "used",
    "need", "want", "good", "best", "better", "also", "if", "so",
}

CATEGORY_KEYWORDS = {
    "motors": ["motor", "kv", "rpm", "stator", "bearing", "windings", "thrust", "t-motor", "emax", "iflight", "2207", "2306", "2204", "brushless"],
    "batteries": ["battery", "lipo", "mah", "4s", "6s", "3s", "voltage", "cell", "charge", "c rating", "storage", "puffing", "swelling", "lithium", "liion", "li-ion"],
    "flight_controllers": ["flight controller", "fc", "betaflight", "pid", "gyro", "uart", "f4", "f7", "f722", "f405", "inav", "ardupilot", "blackbox", "osd", "rpm filter"],
    "troubleshooting": ["won't", "not working", "problem", "issue", "fix", "error", "crash", "flip", "oscillat", "vibrat", "help", "broken", "fail", "stuck", "drift", "beep"],
    "building": ["build", "solder", "frame", "tool", "assemble", "wire", "connect", "install", "xt60", "smoke stopper", "standoff", "mount"],
    "fpv_systems": ["fpv", "goggles", "analog", "digital", "dji", "vtx", "camera", "video", "latency", "walksnail", "hdzero", "fatshark", "skyzone", "goggle"],
    "radio_receiver": ["receiver", "transmitter", "radio", "bind", "elrs", "frsky", "crossfire", "signal", "tbs", "expresslrs", "opentx", "edgetx", "failsafe", "rx", "tx"],
    "safety": ["safety", "safe", "legal", "regulation", "law", "failsafe", "emergency", "faa", "caa", "register", "rules"],
    "esc": ["esc", "speed controller", "blheli", "am32", "dshot", "oneshot", "pwm", "calibrat", "current"],
    "props": ["prop", "propeller", "blade", "hq", "dal", "gemfan", "pitch", "5inch", "3inch", "4inch", "6inch", "tri-blade"],
    "gps": ["gps", "satellite", "gnss", "return to home", "rth", "position hold", "altitude hold", "loiter", "rescue"],
}

# Component categories that map to DB component_types
COMPONENT_CATEGORY_MAP = {
    "motors": "motor",
    "batteries": "battery",
    "flight_controllers": "flight_controller",
    "esc": "esc",
    "fpv_systems": "camera",
    "radio_receiver": "receiver",
    "props": "propeller",
}


# ──────────────────────────────────────────────
# Keyword & Category Helpers
# ──────────────────────────────────────────────

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


def _score_doc(doc: dict, keywords: list[str], category: Optional[str]) -> float:
    """Score a document by keyword overlap + category match."""
    score = 0.0
    doc_kws = set(doc.get("keywords", []))
    kw_set = set(keywords)

    # Keyword overlap (weighted by match count)
    overlap = len(kw_set & doc_kws)
    score += overlap * 2.0

    # Category exact match bonus
    if category and doc.get("category") == category:
        score += 3.0

    # Difficulty bonus for beginner questions
    if doc.get("difficulty") == "beginner":
        score += 0.5

    return score


# ──────────────────────────────────────────────
# Primary Knowledge Search
# ──────────────────────────────────────────────

async def search_knowledge(
    question: str,
    keywords: list[str],
    category: Optional[str],
) -> Optional[dict]:
    """
    Multi-stage knowledge search:
    1. Keyword + category match (precise)
    2. Text search (broad coverage)
    3. Category-only fallback
    """
    db = get_db()
    if db is None:
        return None

    # Stage 1: keyword + category match
    query: dict = {}
    if category:
        query["category"] = category
    if keywords:
        query["keywords"] = {"$in": keywords[:8]}

    docs = await db.drone_knowledge.find(query).limit(10).to_list(length=10)
    if docs:
        return max(docs, key=lambda d: _score_doc(d, keywords, category))

    # Stage 2: text search (requires text index on question+answer)
    try:
        search_str = " ".join(keywords[:6])
        text_docs = await db.drone_knowledge.find(
            {"$text": {"$search": search_str}},
            {"score": {"$meta": "textScore"}},
        ).sort([("score", {"$meta": "textScore"})]).limit(5).to_list(length=5)

        if text_docs:
            return text_docs[0]
    except Exception:
        pass  # Text index may not exist yet; gracefully skip

    # Stage 3: category-only fallback
    if category:
        cat_docs = await db.drone_knowledge.find(
            {"category": category}
        ).limit(3).to_list(length=3)
        if cat_docs:
            return cat_docs[0]

    return None


# ──────────────────────────────────────────────
# Troubleshooting Search
# ──────────────────────────────────────────────

async def search_troubleshooting(question: str) -> Optional[dict]:
    """Search troubleshooting_cases by problem, symptoms, and keywords."""
    db = get_db()
    if db is None:
        return None

    keywords = extract_keywords(question)
    category = classify_category(question)

    conditions = []

    # Keyword match in problem title
    if keywords:
        conditions.append({
            "problem": {"$regex": "|".join(re.escape(k) for k in keywords[:5]), "$options": "i"}
        })
        # Keyword match in keywords array
        conditions.append({"keywords": {"$in": keywords[:6]}})

    # Category match
    if category:
        conditions.append({"category": {"$regex": category, "$options": "i"}})

    query = {"$or": conditions} if conditions else {}
    docs = await db.troubleshooting_cases.find(query).limit(5).to_list(length=5)

    if docs:
        # Score by keyword overlap in problem + symptoms
        def score_ts(doc):
            s = 0
            text = (doc.get("problem", "") + " " + " ".join(doc.get("symptoms", []))).lower()
            s += sum(1 for kw in keywords if kw in text)
            s += len(set(keywords) & set(doc.get("keywords", []))) * 2
            return s
        return max(docs, key=score_ts)

    # Text search fallback
    try:
        search_str = " ".join(keywords[:5])
        text_docs = await db.troubleshooting_cases.find(
            {"$text": {"$search": search_str}},
            {"score": {"$meta": "textScore"}},
        ).sort([("score", {"$meta": "textScore"})]).limit(3).to_list(length=3)
        if text_docs:
            return text_docs[0]
    except Exception:
        pass

    return None


# ──────────────────────────────────────────────
# Component Search (for chat context injection)
# ──────────────────────────────────────────────

async def search_components_for_chat(
    category: Optional[str],
    keywords: list[str],
    limit: int = 3,
) -> list[dict]:
    """
    Find relevant components to surface in chat responses.
    Maps chat category to component_type and searches.
    """
    db = get_db()
    if db is None:
        return []

    component_type = COMPONENT_CATEGORY_MAP.get(category)
    query: dict = {}

    if component_type:
        query["component_type"] = component_type

    # Filter by use-case keywords that appear in use_cases field
    use_kws = [k for k in keywords if k in ["racing", "freestyle", "cinewhoop", "long_range", "longrange"]]
    if use_kws:
        query["use_cases"] = {"$in": use_kws}

    docs = await db.drone_components.find(query).sort("rating", -1).limit(limit).to_list(length=limit)

    # If no results with use_cases filter, retry without it
    if not docs and component_type:
        docs = await db.drone_components.find(
            {"component_type": component_type}
        ).sort("rating", -1).limit(limit).to_list(length=limit)

    return docs


# ──────────────────────────────────────────────
# Related Topics Sidebar
# ──────────────────────────────────────────────

async def get_related_topics(category: Optional[str], limit: int = 3) -> list[dict]:
    """Return related Q&A titles for the sidebar."""
    db = get_db()
    if db is None or not category:
        return []
    cursor = db.drone_knowledge.find(
        {"category": category},
        {"question": 1, "_id": 1}
    ).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [{"title": d["question"], "id": str(d["_id"])} for d in docs]


# ──────────────────────────────────────────────
# Format helpers
# ──────────────────────────────────────────────

def format_troubleshooting_context(doc: dict) -> str:
    """Convert a troubleshooting doc into clean context string for the AI prompt."""
    lines = [f"Problem: {doc.get('problem', '')}"]

    symptoms = doc.get("symptoms", [])
    if symptoms:
        lines.append(f"Symptoms: {', '.join(symptoms)}")

    causes = doc.get("possible_causes", [])
    if causes:
        lines.append("\nPossible Causes (most likely first):")
        for i, c in enumerate(causes, 1):
            prob = c.get("probability", "")
            diff = c.get("difficulty", "")
            lines.append(f"{i}. {c.get('cause', '')} [{prob} probability, {diff} fix]")
            lines.append(f"   → Solution: {c.get('solution', '')}")

    steps = doc.get("diagnostic_steps", [])
    if steps:
        lines.append("\nDiagnostic Steps:")
        for i, step in enumerate(steps, 1):
            lines.append(f"{i}. {step}")

    return "\n".join(lines)


def format_component_context(components: list[dict]) -> str:
    """Format component specs for AI injection."""
    if not components:
        return ""
    lines = []
    for c in components:
        specs = c.get("specs", {})
        spec_str = ", ".join(f"{k}: {v}" for k, v in specs.items())
        lines.append(
            f"- **{c.get('name')}** ({c.get('brand')}) — {spec_str} | "
            f"Price: ${c.get('price_range', 'N/A')} | Rating: {c.get('rating', 0)}/5"
        )
    return "\n".join(lines)
