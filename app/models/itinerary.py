from typing import List, Optional
from pydantic import BaseModel


class Place(BaseModel):
    name: str
    category: Optional[str] = None
    cost: Optional[int] = 0
    time_required: Optional[int] = 0
    description: Optional[str] = None


class DayPlan(BaseModel):
    day: int
    places: List[Place]


class ItineraryRequest(BaseModel):
    days: int
    budget: int
    interests: List[str]
    must_visit: Optional[List[str]] = []
    travelers: int


class ItineraryResponse(BaseModel):
    city: Optional[str] = None
    total_days: int
    total_budget: int
    plan: List[DayPlan]
