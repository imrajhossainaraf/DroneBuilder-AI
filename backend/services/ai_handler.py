"""
DroneMate AI Handler
- Auto: parallel race (Ollama, OpenRouter, Groq, OpenAI) then Gemini fallback
- Single-provider mode when user selects a specific agent
- All calls are async-safe (run in thread pool)
- Prompt builder injects DB context, category expertise, and conversation history
"""
import asyncio
import requests
import config


# ──────────────────────────────────────────────
# SYSTEM PROMPT CORE
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are DroneMate, a world-class drone building and FPV expert assistant.
You have deep hands-on knowledge of:
- FPV racing and freestyle drone hardware (motors, ESCs, flight controllers, frames, batteries, props)
- Betaflight / iNAV / ArduPilot configuration, PID tuning, blackbox analysis
- FPV video systems (analog, DJI, Walksnail, HDZero)
- Radio systems (ExpressLRS, TBS Crossfire, FrSky, Spektrum)
- Soldering, wiring, and build techniques
- **Bangladesh Regulations**: Deep knowledge of CAAB (Civil Aviation Authority of Bangladesh) 2026 rules. Awareness of No-Fly Zones like Chittagong Port, Airports, and KPIs. Knowledge of the 200ft AGL limit and 250g registration rules.
- **Local Market**: Expertise in BDT (Bangladeshi Taka) pricing, part availability in BD, and environmental challenges like salt-air corrosion in coastal areas (Chattogram/Cox's Bazar).
- Troubleshooting: arming issues, oscillations, ESC problems, video interference, signal loss

RESPONSE RULES:
1. Be specific — use real part names, exact values (KV, voltage, current ratings)
2. Use numbered steps for procedures
3. Use **bold** for component names and important values
4. Flag safety risks with ⚠️
5. If diagnosing a problem, list causes in order of probability (most likely first)
6. Be concise — aim for 150-400 words unless the topic demands more
7. Never make up specifications — say "check your manufacturer's documentation" if unsure
8. **COMPETITION ADVICE**: When asked for opinions, comparisons, or recommendations (e.g., 5-inch vs 6-inch), DO NOT JUST LIST PROS AND CONS. Give a highly opinionated, persuasive answer on what it takes to **WIN COMPETITIONS**. Act like an elite FPV drone champion. Be decisive.
9. **CASUAL CONVERSATION**: If the user engages in casual small talk (e.g., "hello", "what time is it"), respond naturally, elegantly, and concisely while steering the conversation back to drones if appropriate.
"""

CATEGORY_EXPERTISE = {
    "motors": "You are in MOTOR EXPERT mode. Focus on KV ratings, stator sizes, voltage compatibility, current draw, and motor pairing with ESCs and props.",
    "batteries": "You are in BATTERY EXPERT mode. Focus on cell count (S rating), capacity (mAh), C rating math, storage voltage, charging safety, and voltage sag.",
    "flight_controllers": "You are in FLIGHT CONTROLLER EXPERT mode. Focus on Betaflight configuration, PID tuning, ports/UARTs, firmware flashing, and filter settings.",
    "troubleshooting": "You are in DIAGNOSTIC EXPERT mode. List possible causes in order of probability. Provide clear step-by-step diagnostic procedures. Be direct about severity.",
    "building": "You are in BUILD EXPERT mode. Focus on soldering technique, component order, safety checks (smoke stopper!), and common beginner mistakes.",
    "fpv_systems": "You are in FPV EXPERT mode. Focus on latency, resolution, band/channel selection, antenna placement, VTX power legality, and noise filtering.",
    "radio_receiver": "You are in RADIO EXPERT mode. Focus on binding procedures, link quality, failsafe configuration, protocol differences, and range optimization.",
    "safety": "You are in SAFETY EXPERT mode. Emphasize regulations, pre-flight checks, failsafe, battery handling, and legal compliance. Use ⚠️ for serious risks.",
    "esc": "You are in ESC EXPERT mode. Focus on current ratings, protocols (DSHOT, PWM, Oneshot), BLHeli configuration, telemetry, and ESC calibration.",
    "props": "You are in PROPELLER EXPERT mode. Focus on prop sizing, pitch, material (polycarbonate vs tri-blade), balancing, and matching to motor KV.",
    "gps": "You are in GPS EXPERT mode. Focus on GPS rescue configuration, satellite acquisition, flight modes (RTH, Position Hold), and hardware setup.",
}


# ──────────────────────────────────────────────
# PRIMARY: Ollama (Local)
# ──────────────────────────────────────────────

def _ollama_generate_sync(prompt: str, num_predict: int = 1024, timeout_sec: float = 3) -> str | None:
    """Synchronous Ollama call — run in thread pool."""
    try:
        resp = requests.post(
            f"{config.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": num_predict},
            },
            timeout=timeout_sec,
        )
        resp.raise_for_status()
        result = resp.json().get("response", "").strip()
        return result if len(result) > 30 else None
    except requests.exceptions.ConnectionError:
        print("[WARN] Ollama not running -- skipping.")
        return None
    except Exception as e:
        print(f"[WARN] Ollama error: {e}")
        return None


async def ollama_generate(prompt: str, num_predict: int = 1024, timeout_sec: float = 3) -> str | None:
    return await asyncio.to_thread(_ollama_generate_sync, prompt, num_predict, timeout_sec)


def check_ollama_status() -> dict:
    try:
        resp = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return {"running": True, "models": models}
    except Exception:
        return {"running": False, "models": []}


# ──────────────────────────────────────────────
# BACKUP 1: OpenRouter (Cloud — Fast, Smart)
# ──────────────────────────────────────────────

def _openrouter_generate_sync(prompt: str, max_tokens: int = 1200) -> str | None:
    if not config.OPENROUTER_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "DroneMate",
            },
            json={
                "model": config.OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.65,
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"].strip()
        return None
    except Exception as e:
        print(f"[WARN] OpenRouter error: {e}")
        return None


async def openrouter_generate(prompt: str, max_tokens: int = 1200) -> str | None:
    return await asyncio.to_thread(_openrouter_generate_sync, prompt, max_tokens)


# ──────────────────────────────────────────────
# BACKUP 2: Groq (Cloud — fast)
# ──────────────────────────────────────────────

def _groq_generate_sync(prompt: str, max_tokens: int = 1200) -> str | None:
    if not config.GROQ_API_KEY:
        return None
    try:
        import groq
        client = groq.Groq(api_key=config.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.65,
        )
        result = completion.choices[0].message.content.strip()
        return result if result else None
    except ImportError:
        print("[INFO] groq package not installed. Run: pip install groq")
        return None
    except Exception as e:
        print(f"[WARN] Groq error: {type(e).__name__}: {e}")
        return None


async def groq_generate(prompt: str, max_tokens: int = 1200) -> str | None:
    return await asyncio.to_thread(_groq_generate_sync, prompt, max_tokens)


# ──────────────────────────────────────────────
# OpenAI (Cloud)
# ──────────────────────────────────────────────

def _openai_generate_sync(prompt: str, max_tokens: int = 1200) -> str | None:
    if not config.OPENAI_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.65,
            },
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"].strip() or None
        return None
    except Exception as e:
        print(f"[WARN] OpenAI error: {e}")
        return None


async def openai_generate(prompt: str, max_tokens: int = 1200) -> str | None:
    return await asyncio.to_thread(_openai_generate_sync, prompt, max_tokens)


# ──────────────────────────────────────────────
# BACKUP 2: Gemini (Cloud)
# ──────────────────────────────────────────────

def _gemini_generate_sync(prompt: str, max_output_tokens: int = 1200) -> str | None:
    if not config.GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            config.GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
        )
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.65, "max_output_tokens": max_output_tokens},
        )
        result = response.text.strip()
        return result if result else None
    except ImportError:
        print("[INFO] google-generativeai not installed. Run: pip install google-generativeai")
        return None
    except Exception as e:
        print(f"[WARN] Gemini error: {e}")
        return None


async def gemini_generate(prompt: str, max_output_tokens: int = 1200) -> str | None:
    return await asyncio.to_thread(_gemini_generate_sync, prompt, max_output_tokens)


# ──────────────────────────────────────────────
# ORCHESTRATOR
# ──────────────────────────────────────────────

def _apply_response_detail(prompt: str, response_detail: str) -> str:
    if response_detail != "detailed":
        return prompt
    return (
        prompt
        + "\n\nDETAIL LEVEL: Provide a comprehensive answer with numbered steps, edge cases, and safety notes. "
        "Expand beyond the usual brevity when the topic warrants it."
    )


def _token_budget(response_detail: str) -> tuple[int, int]:
    """Returns (max_tokens for APIs, num_predict for Ollama)."""
    if response_detail == "detailed":
        return 2500, 2048
    return 1200, 1024


VALID_PROVIDERS = frozenset({"auto", "ollama", "openai", "groq", "openrouter", "gemini"})


async def _race_providers(full_prompt: str, max_tokens: int, num_predict: int) -> tuple[str, str]:
    tasks = []
    tasks.append(
        asyncio.create_task(
            ollama_generate(full_prompt, num_predict, timeout_sec=15),
            name=f"ollama/{config.OLLAMA_MODEL}",
        )
    )
    if config.OPENROUTER_API_KEY:
        tasks.append(
            asyncio.create_task(
                openrouter_generate(full_prompt, max_tokens), name=f"openrouter/{config.OPENROUTER_MODEL}"
            )
        )
    if config.GROQ_API_KEY:
        tasks.append(
            asyncio.create_task(groq_generate(full_prompt, max_tokens), name=f"groq/{config.GROQ_MODEL}")
        )
    if config.OPENAI_API_KEY:
        tasks.append(
            asyncio.create_task(openai_generate(full_prompt, max_tokens), name=f"openai/{config.OPENAI_MODEL}")
        )

    pending = tasks
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=10)
        for task in done:
            try:
                result = task.result()
            except Exception as e:
                print(f"[WARN] Provider task error: {e}")
                result = None
            if result:
                for p in pending:
                    p.cancel()
                return result, task.get_name()
        if not done and not pending:
            break

    result = await gemini_generate(full_prompt, max_tokens)
    if result:
        return result, f"gemini/{config.GEMINI_MODEL}"

    return (
        "⚠️ I'm currently unable to reach any AI service quickly. "
        "Your question has been logged and the database may still have relevant information above.",
        "none",
    )


async def get_ai_response(
    prompt: str,
    provider: str = "auto",
    response_detail: str = "standard",
) -> tuple[str, str]:
    """
    provider: auto (parallel race), or ollama | openai | groq | openrouter | gemini (single backend).
    response_detail: standard | detailed — longer answers and higher token limits when detailed.
    Returns (response_text, model_name_used).
    """
    rd = response_detail if response_detail in ("standard", "detailed") else "standard"
    full_prompt = _apply_response_detail(prompt, rd)
    max_tokens, num_predict = _token_budget(rd)

    p = (provider or "auto").lower().strip()
    if p not in VALID_PROVIDERS:
        p = "auto"

    if p == "auto":
        return await _race_providers(full_prompt, max_tokens, num_predict)

    if p == "ollama":
        # Local inference often exceeds a few seconds; allow time when user explicitly picks Ollama
        r = await ollama_generate(full_prompt, num_predict, timeout_sec=180)
        if r:
            return r, f"ollama/{config.OLLAMA_MODEL}"
        return (
            "⚠️ Ollama did not return a usable response. Check that Ollama is running and the model is available.",
            "none",
        )

    if p == "openai":
        if not config.OPENAI_API_KEY:
            return "⚠️ OpenAI is not configured. Set OPENAI_API_KEY in backend/.env.", "none"
        r = await openai_generate(full_prompt, max_tokens)
        if r:
            return r, f"openai/{config.OPENAI_MODEL}"
        return "⚠️ OpenAI request failed. Check your API key and model name.", "none"

    if p == "groq":
        if not config.GROQ_API_KEY:
            return "⚠️ Groq is not configured. Set GROQ_API_KEY in backend/.env.", "none"
        r = await groq_generate(full_prompt, max_tokens)
        if r:
            return r, f"groq/{config.GROQ_MODEL}"
        return "⚠️ Groq request failed. Check your API key.", "none"

    if p == "openrouter":
        if not config.OPENROUTER_API_KEY:
            return "⚠️ OpenRouter is not configured. Set OPENROUTER_API_KEY in backend/.env.", "none"
        r = await openrouter_generate(full_prompt, max_tokens)
        if r:
            return r, f"openrouter/{config.OPENROUTER_MODEL}"
        return "⚠️ OpenRouter request failed. Check your API key.", "none"

    if p == "gemini":
        if not config.GEMINI_API_KEY:
            return "⚠️ Gemini is not configured. Set GEMINI_API_KEY in backend/.env.", "none"
        r = await gemini_generate(full_prompt, max_tokens)
        if r:
            return r, f"gemini/{config.GEMINI_MODEL}"
        return "⚠️ Gemini request failed. Check your API key and model name.", "none"

    return await _race_providers(full_prompt, max_tokens, num_predict)


def provider_flags() -> dict:
    """Which backends have keys configured (for UI / status)."""
    return {
        "openai_configured": bool(config.OPENAI_API_KEY),
        "groq_configured": bool(config.GROQ_API_KEY),
        "gemini_configured": bool(config.GEMINI_API_KEY),
        "openrouter_configured": bool(config.OPENROUTER_API_KEY),
    }


# ──────────────────────────────────────────────
# PROMPT BUILDER
# ──────────────────────────────────────────────

def build_prompt(
    question: str,
    db_context: str | None = None,
    category: str = "",
    conversation_history: list[dict] | None = None,
    component_context: str | None = None,
    user_time: str | None = None,
) -> str:
    """
    Build a highly focused drone-expert prompt.
    - Injects DB knowledge as verified reference
    - Injects real component specs when available
    - Includes last 3 conversation turns for context
    - Gives the AI category-specific expertise framing
    """
    parts = []

    # Category expertise framing
    if category and category in CATEGORY_EXPERTISE:
        parts.append(CATEGORY_EXPERTISE[category])
        parts.append("")

    if user_time:
        parts.append(f"CURRENT SYSTEM TIME: {user_time}")
        parts.append("")

    # Conversation history (last 3 turns for context)
    if conversation_history:
        recent = conversation_history[-6:]  # last 3 user+assistant pairs
        history_text = []
        for msg in recent:
            role = "User" if msg.get("role") == "user" else "DroneMate"
            history_text.append(f"{role}: {msg.get('content', '')}")
        if history_text:
            parts.append("CONVERSATION HISTORY (for context):")
            parts.append("\n".join(history_text))
            parts.append("")

    # Verified DB knowledge
    if db_context:
        parts.append("VERIFIED KNOWLEDGE BASE INFORMATION:")
        parts.append(db_context)
        parts.append("")
        parts.append("Use the verified information above as your primary source. Expand on it with additional practical details, but do not contradict it.")
        parts.append("")

    # Real component specs
    if component_context:
        parts.append("REAL COMPONENT SPECIFICATIONS FROM DATABASE:")
        parts.append(component_context)
        parts.append("")

    # The actual question
    parts.append(f"USER QUESTION: {question}")
    parts.append("")
    parts.append("Provide a thorough, practical answer following the response rules:")

    return "\n".join(parts)
