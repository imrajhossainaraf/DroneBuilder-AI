import requests
import config

# ──────────────────────────────────────────────
# PRIMARY: Ollama (Local)
# ──────────────────────────────────────────────

def ollama_generate(prompt: str) -> str | None:
    """Call local Ollama instance. Returns text or None on failure."""
    try:
        resp = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json().get("response", "").strip()
        if len(result) > 30:
            return result
        return None
    except requests.exceptions.ConnectionError:
        print("⚠️  Ollama is not running. Start with: ollama serve")
        return None
    except Exception as e:
        print(f"⚠️  Ollama error: {e}")
        return None


def check_ollama_status() -> dict:
    """Check whether Ollama is running and which models are available."""
    try:
        resp = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return {"running": True, "models": models}
    except Exception:
        return {"running": False, "models": []}


# ──────────────────────────────────────────────
# BACKUP 1: Groq (Cloud)
# ──────────────────────────────────────────────

def groq_generate(prompt: str) -> str | None:
    """Call Groq Cloud API. Returns text or None if key missing/fails."""
    if not config.GROQ_API_KEY:
        print("ℹ️  Groq API key not configured — skipping.")
        return None
    try:
        import groq  # optional dependency
        client = groq.Groq(api_key=config.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )
        result = completion.choices[0].message.content.strip()
        return result if result else None
    except ImportError:
        print("ℹ️  groq package not installed. Run: pip install groq")
        return None
    except Exception as e:
        print(f"⚠️  Groq error: {e}")
        return None


# ──────────────────────────────────────────────
# BACKUP 2: Gemini (Cloud)
# ──────────────────────────────────────────────

def gemini_generate(prompt: str) -> str | None:
    """Call Google Gemini API. Returns text or None if key missing/fails."""
    if not config.GEMINI_API_KEY:
        print("ℹ️  Gemini API key not configured — skipping.")
        return None
    try:
        import google.generativeai as genai  # optional dependency
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        response = model.generate_content(prompt)
        result = response.text.strip()
        return result if result else None
    except ImportError:
        print("ℹ️  google-generativeai not installed. Run: pip install google-generativeai")
        return None
    except Exception as e:
        print(f"⚠️  Gemini error: {e}")
        return None


# ──────────────────────────────────────────────
# ORCHESTRATOR
# ──────────────────────────────────────────────

def get_ai_response(prompt: str) -> tuple[str, str]:
    """
    Try AI providers in priority order.
    Returns (response_text, model_name_used).
    """
    # 1. Ollama (local — always try first)
    result = ollama_generate(prompt)
    if result:
        return result, f"ollama/{config.OLLAMA_MODEL}"

    # 2. Groq (cloud backup)
    result = groq_generate(prompt)
    if result:
        return result, f"groq/{config.GROQ_MODEL}"

    # 3. Gemini (final backup)
    result = gemini_generate(prompt)
    if result:
        return result, f"gemini/{config.GEMINI_MODEL}"

    # All failed
    return (
        "I'm currently unable to reach any AI service. "
        "Please make sure Ollama is running (`ollama serve`) or add API keys in your .env file.",
        "none",
    )


def build_prompt(question: str, db_context: str | None = None, category: str = "") -> str:
    """Build a focused drone-assistant prompt."""
    system = (
        "You are DroneMate, an expert drone building and FPV assistant. "
        "You give clear, practical, accurate answers about drone hardware, "
        "Betaflight configuration, troubleshooting, and safety. "
        "Be concise and structured. Use numbered steps where helpful."
    )
    if db_context:
        return (
            f"{system}\n\n"
            f"REFERENCE INFORMATION FROM DATABASE:\n{db_context}\n\n"
            f"USER QUESTION: {question}\n\n"
            f"Using the reference above as a starting point, give a thorough answer:"
        )
    return (
        f"{system}\n\n"
        f"USER QUESTION: {question}\n\n"
        f"Answer:"
    )
