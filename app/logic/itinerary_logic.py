from app.logic.mock_data import mock_attractions
from app.services.ors_service import get_travel_time

def generate_itinerary_with_ors(days: int, budget: int, preferences: list[str], daily_hours: int = 8):
    selected = []  # after scoring + budget filtering
    itinerary = {f"Day {i+1}": [] for i in range(days)}

    day = 1
    hours_used = 0
    last_location = None

    for attraction in mock_attractions:
        visit_time = attraction["time_hours"]
        travel_time = 0

        if last_location:
            travel_time = get_travel_time(last_location["coords"], attraction["coords"]) / 60

        total_time = visit_time + travel_time

        if hours_used + total_time > daily_hours:
            day += 1
            if day > days:
                break
            hours_used = 0

        itinerary[f"Day {day}"].append({
            "place": attraction["name"],
            "visit_time": visit_time,
            "travel_time": travel_time
        })

        hours_used += total_time
        last_location = attraction

    return itinerary
