"""
DroneMate Build Recommender
- Takes budget, drone type, skill level
- Queries components DB for matching parts within budget
- Uses AI to generate a personalized recommendation narrative
"""
import uuid
from fastapi import APIRouter, HTTPException
from models.schemas import RecommendRequest
from models.database import get_db
from services.ai_handler import get_ai_response
from utils.helpers import mongo_doc_to_dict

router = APIRouter(prefix="/api/recommend", tags=["recommend"])

# Rough budget allocations by component type (percentage of total budget)
BUDGET_ALLOCATION = {
    "racing": {
        "frame": 0.12,
        "motor": 0.20,            # x4
        "esc": 0.18,
        "flight_controller": 0.15,
        "battery": 0.15,          # x2 packs
        "fpv_camera": 0.06,
        "vtx": 0.07,
        "receiver": 0.07,
    },
    "freestyle": {
        "frame": 0.13,
        "motor": 0.22,
        "esc": 0.17,
        "flight_controller": 0.14,
        "battery": 0.16,
        "fpv_camera": 0.07,
        "vtx": 0.06,
        "receiver": 0.05,
    },
    "long_range": {
        "frame": 0.12,
        "motor": 0.18,
        "esc": 0.15,
        "flight_controller": 0.13,
        "battery": 0.20,
        "fpv_camera": 0.07,
        "vtx": 0.08,
        "receiver": 0.07,
    },
    "micro": {
        "frame": 0.08,
        "motor": 0.22,
        "esc": 0.15,
        "flight_controller": 0.18,
        "battery": 0.20,
        "fpv_camera": 0.10,
        "vtx": 0.07,
    },
    "cinewhoop": {
        "frame": 0.15,
        "motor": 0.20,
        "esc": 0.15,
        "flight_controller": 0.13,
        "battery": 0.17,
        "fpv_camera": 0.10,
        "vtx": 0.05,
        "receiver": 0.05,
    },
}


def _parse_price_range(price_range: str) -> float:
    """Return midpoint of a price range string like '15-20'."""
    try:
        parts = str(price_range).split("-")
        nums = [float(p.strip()) for p in parts if p.strip().replace(".", "").isdigit()]
        return sum(nums) / len(nums) if nums else 999
    except Exception:
        return 999


async def _find_component(db, component_type: str, max_price: float, use_cases: list[str]) -> dict | None:
    """Find the best-rated component within budget for the given type."""
    query: dict = {"component_type": component_type}
    if use_cases:
        query["use_cases"] = {"$in": use_cases}

    docs = await db.drone_components.find(query).sort("rating", -1).limit(20).to_list(length=20)

    # Filter by price range
    affordable = [
        d for d in docs
        if _parse_price_range(d.get("price_range", "9999")) <= max_price
    ]

    if affordable:
        return affordable[0]

    # Fallback: ignore use_case filter
    all_type_docs = await db.drone_components.find(
        {"component_type": component_type}
    ).sort("rating", -1).limit(20).to_list(length=20)
    affordable2 = [
        d for d in all_type_docs
        if _parse_price_range(d.get("price_range", "9999")) <= max_price
    ]
    return affordable2[0] if affordable2 else None


@router.post("/")
async def recommend_build(req: RecommendRequest):
    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    drone_type = req.drone_type.lower().replace(" ", "_")
    allocation = BUDGET_ALLOCATION.get(drone_type, BUDGET_ALLOCATION["freestyle"])
    use_cases = [drone_type]
    if req.use_case:
        use_cases.append(req.use_case.lower())

    # Find components within budget allocation
    build = {}
    total_cost = 0.0
    parts_summary = []

    for comp_type, fraction in allocation.items():
        max_price = req.budget * fraction
        # Motors cost is per-4 pack, so budget is for all 4
        if comp_type == "motor":
            max_price_per_unit = max_price / 4
        else:
            max_price_per_unit = max_price

        component = await _find_component(db, comp_type, max_price_per_unit, use_cases)
        if component:
            c = mongo_doc_to_dict(component)
            qty = 4 if comp_type == "motor" else (2 if comp_type == "battery" else 1)
            unit_price = _parse_price_range(c.get("price_range", "0"))
            item_cost = unit_price * qty
            total_cost += item_cost
            build[comp_type] = c
            specs = c.get("specs", {})
            spec_str = ", ".join(f"{k}: {v}" for k, v in list(specs.items())[:3])
            parts_summary.append(
                f"- {comp_type.upper()} (x{qty}): {c.get('name')} ({c.get('brand')}) — {spec_str} | ~${unit_price:.0f} each = ${item_cost:.0f}"
            )

    # Build AI prompt for recommendation narrative
    prompt = f"""
A beginner is asking for a drone build recommendation. Generate a friendly, encouraging, and practical response.

BUILD REQUEST:
- Drone Type: {req.drone_type}
- Budget: ${req.budget} USD
- Skill Level: {req.skill_level}
- Use Case: {req.use_case or 'general'}
- Preferred Battery: {req.preferred_battery or 'no preference'}

PARTS FOUND IN DATABASE (within budget):
{chr(10).join(parts_summary) if parts_summary else "No exact matches found — provide general guidance."}

Estimated Total Cost: ${total_cost:.0f}

Write a complete build recommendation that:
1. Names each part with why it was chosen
2. Highlights what makes this build good for a {req.skill_level}
3. Notes 1-2 things to watch out for (soldering, ESC protocol setup, etc.)
4. Gives encouragement and next steps
Keep it practical, friendly, and specific.
"""

    ai_text, model_used = await get_ai_response(prompt)

    return {
        "session_id": req.session_id or str(uuid.uuid4()),
        "drone_type": req.drone_type,
        "budget": req.budget,
        "estimated_total": round(total_cost, 2),
        "parts": {k: {"name": v.get("name"), "brand": v.get("brand"), "price_range": v.get("price_range")} for k, v in build.items()},
        "recommendation": ai_text,
        "ai_model": model_used,
    }
