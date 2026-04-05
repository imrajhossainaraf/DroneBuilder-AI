from pydantic import BaseModel
from typing import Optional, List, Any, Literal
from datetime import datetime


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    ai_provider: Literal["auto", "ollama", "openai", "groq", "openrouter", "gemini"] = "auto"
    response_detail: Literal["standard", "detailed"] = "standard"


class ChatResponse(BaseModel):
    response: str
    source: str  # "database", "ai", "database_enhanced", "error"
    ai_model: Optional[str] = None
    confidence: Optional[float] = None
    related_topics: List[dict] = []
    suggested_questions: List[str] = []
    relevant_components: List[dict] = []   # Component cards surfaced from DB
    session_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    conversation_id: str
    question: str
    answer_provided: str
    was_helpful: bool
    feedback_text: Optional[str] = None


class RecommendRequest(BaseModel):
    budget: int                         # USD total budget
    drone_type: str                     # racing | freestyle | cinewhoop | long_range | micro
    skill_level: str                    # beginner | intermediate | advanced
    use_case: Optional[str] = None     # e.g. "outdoor racing", "cinematic filming"
    preferred_battery: Optional[str] = None  # "4S" | "6S"
    session_id: Optional[str] = None


class PartItem(BaseModel):
    component_type: str
    name: str
    quantity: int = 1
    estimated_cost: Optional[float] = None
    buy_link: Optional[str] = None


class BuildStep(BaseModel):
    step_number: int
    title: str
    description: str
    duration: Optional[str] = None
    tips: List[str] = []
    warning: Optional[str] = None      # ⚠️ danger flags


class BuildGuide(BaseModel):
    id: Optional[str] = None
    title: str
    drone_type: str
    difficulty: str
    estimated_time: str
    budget: str
    required_tools: List[str] = []
    parts_list: List[PartItem] = []    # Full parts list with costs
    total_component_cost: Optional[float] = None
    steps: List[BuildStep] = []
    tags: List[str] = []
    video_url: Optional[str] = None


class Component(BaseModel):
    id: Optional[str] = None
    component_type: str
    name: str
    brand: str
    specs: dict
    price_range: Optional[str] = None
    compatible_with: Optional[dict] = None
    use_cases: List[str] = []
    pros: List[str] = []
    cons: List[str] = []
    rating: float = 0.0
