# app/logic/scoring.py

from typing import Dict, List

DEFAULT_VISIT_TIME_HR = 2.0          # if dataset has no visit time column
TRAVEL_SAME_CITY_HR = 0.25           # heuristic intra-day overhead
TRAVEL_SWITCH_CITY_HR = 0.5          # heuristic when city changes
DAILY_ACTIVITY_HOURS = 8.0

INTEREST_KEYS = [
    "Waterfalls_Lakes", "History", "Nature", "Adventure",
    "Beaches", "Religious_Spiritual", "National_Parks_Wildlife",
    "Hiking_Mountain", "Gardens_Botanical", "Urban_City",
    "Ayurveda_Wellness", "Water_Sports"
]

def interest_to_col(interest: str) -> str:
    # "history" -> "Category_History"
    return f"Category_{interest.strip().replace(' ', '_').title()}"

def compute_interest_score(row: Dict, interests: List[str]) -> float:
    # Simple sum of matching interest flags; you can weight later
    score = 0.0
    for intr in interests or []:
        col = interest_to_col(intr)
        if col in row and int(row[col]) == 1:
            score += 1.0
    return score

def visit_time_hr(row: Dict) -> float:
    if "Visit_Time_hr" in row and row["Visit_Time_hr"]:
        try:
            return float(row["Visit_Time_hr"])
        except Exception:
            return 2.0
    return 2.0
