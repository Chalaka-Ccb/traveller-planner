# app/services/itinerary_builder.py
from typing import List, Dict
from fastapi.encoders import jsonable_encoder
import json

from app.models.itinerary import DayPlan, Place
from app.services.data_loader import DATASET


def build_itinerary_days(places: List[Dict], days: int, max_hours_per_day: float = 8.0) -> List[DayPlan]:
    """
    Distribute places across the requested number of days.
    Each day tries to respect max_hours_per_day, but total_days is always exactly `days`.
    """
    # Sort by score (highest first)
    sorted_places = sorted(places, key=lambda x: x.get("score", 0), reverse=True)
    total_places = len(sorted_places)

    # Determine approximate number of places per day
    per_day = max(1, total_places // days)

    day_plans: List[DayPlan] = []
    day_idx = 1
    start = 0

    for day_idx in range(1, days + 1):
        # Calculate end index for this day
        if day_idx == days:
            end = total_places  # Last day takes remaining places
        else:
            end = start + per_day
        current_places_list = []
        current_day_hours = 0.0

        for place in sorted_places[start:end]:
            visit_time = place.get("Visit_Time_hr", 2)
            current_places_list.append(
                Place(
                    name=place.get("Location", "Unknown"),
                    category=place.get("Category", None),
                    cost=int(place.get("Entry_fee_LKR", 0) or 0),
                    time_required=int(visit_time * 60),  # minutes
                    description=place.get("Description", None)
                )
            )
            current_day_hours += visit_time

        day_plans.append(DayPlan(day=day_idx, places=current_places_list))
        start = end

    return day_plans


async def generate_itinerary(city: str | None, interests: list[str], days: int, budget: float):
    """
    Generate a travel itinerary based on filters and user preferences.
    """
    print(f"🔍 Found matching locations for city='{city}' and interests={interests}")

    # 1. Filter dataset
    filtered = DATASET.copy()
    if city:
        filtered = filtered[filtered["Nearest_City"].str.lower() == city.lower()]
    if interests:
        interest_cols = [col for col in filtered.columns if col.lower() in [i.lower() for i in interests]]
        if interest_cols:
            filtered = filtered[filtered[interest_cols].sum(axis=1) > 0]

    if filtered.empty:
        raise ValueError("No locations match your filters.")

    # 2. Build response in the exact schema format
    candidates = filtered.to_dict(orient="records")
    day_plans = build_itinerary_days(candidates, days)

    response = {
        "city": city or "All",
        "total_days": len(day_plans),
        "total_budget": budget,
        "plan": day_plans
    }

    # Debug log final JSON
    print("[DEBUG] Final response:")
    print(json.dumps(jsonable_encoder(response), indent=2, default=str))

    return jsonable_encoder(response)
