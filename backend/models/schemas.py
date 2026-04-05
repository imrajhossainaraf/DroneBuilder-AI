from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    source: str  # "database", "ai", "database_enhanced"
    ai_model: Optional[str] = None
    confidence: Optional[float] = None
    related_topics: List[dict] = []
    suggested_questions: List[str] = []
    session_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    conversation_id: str
    question: str
    answer_provided: str
    was_helpful: bool
    feedback_text: Optional[str] = None


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


class BuildStep(BaseModel):
    step_number: int
    title: str
    description: str
    duration: Optional[str] = None
    tips: List[str] = []


class BuildGuide(BaseModel):
    id: Optional[str] = None
    title: str
    drone_type: str
    difficulty: str
    estimated_time: str
    budget: str
    required_tools: List[str] = []
    steps: List[BuildStep] = []
    video_url: Optional[str] = None
