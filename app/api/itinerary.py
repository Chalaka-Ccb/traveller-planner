from fastapi import APIRouter, Query
from typing import List
from app.models.itinerary import ItineraryRequest, ItineraryResponse
from app.services.itinerary_builder import build_itinerary_days
from app.services.data_loader import get_locations

router = APIRouter(prefix="/api", tags=["Itinerary"])


@router.post("/generate", response_model=ItineraryResponse)
def generate_itinerary(request: ItineraryRequest):
    # 1. Fetch candidate places
    candidates = get_locations(interests=request.interests)

    # 2. Score places based on categories
    for place in candidates:
        place["score"] = sum(place.get(cat, 0) for cat in [
            "Category_History", "Category_Nature", "Category_Adventure",
            "Category_Beaches", "Category_Religious_Spiritual",
            "Category_National_Parks_Wildlife", "Category_Hiking_Mountain",
            "Category_Gardens_Botanical", "Category_Urban_City",
            "Category_Ayurveda_Wellness", "Category_Water_Sports"
        ])

    # 3. Build day plans (list of DayPlan objects)
    day_plans = build_itinerary_days(candidates, request.days)

    return {
        "city": None,
        "total_days": request.days,
        "total_budget": request.budget,
        "plan": [dp.dict() for dp in day_plans]  # convert Pydantic objects to dict
    }
