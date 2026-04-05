import re

STOP_WORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "with", "my", "i", "what", "how",
    "why", "when", "do", "does", "should", "can", "will", "would",
    "could", "please", "help", "me", "have", "has", "be", "are",
    "its", "up", "this", "that", "so", "just", "need", "want",
    "about", "which", "get", "use", "used", "if", "not", "no",
}


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful words, filtering stop words and short tokens."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 2]


def classify_category(text: str) -> str | None:
    """Return best-matching category name or None."""
    text_lower = text.lower()
    category_keywords = {
        "motors":            ["motor", "kv", "rpm", "stator", "bearing", "thrust", "winding"],
        "batteries":         ["battery", "lipo", "mah", "4s", "6s", "3s", "voltage", "cell", "charge", "c rating", "puff"],
        "flight_controllers":["flight controller", "fc", "betaflight", "pid", "gyro", "uart", "f4", "f7", "firmware", "flash"],
        "troubleshooting":   ["won't", "wont", "not working", "problem", "issue", "fix", "error", "crash", "flip", "oscillat", "vibrat", "beep", "arm"],
        "building":          ["build", "solder", "frame", "tool", "assemble", "wire", "connect", "install", "xt60", "smoke"],
        "fpv_systems":       ["fpv", "goggles", "analog", "digital", "dji", "vtx", "camera", "video", "latency", "jello"],
        "radio_receiver":    ["receiver", "transmitter", "radio", "bind", "elrs", "frsky", "crossfire", "signal", "rc"],
        "safety":            ["safety", "safe", "legal", "regulation", "law", "failsafe", "emergency", "register"],
    }
    scores = {cat: sum(1 for kw in kws if kw in text_lower) for cat, kws in category_keywords.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def format_response_markdown(text: str) -> str:
    """Light cleanup — ensure response text is clean."""
    text = text.strip()
    # Collapse more than 2 blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text
