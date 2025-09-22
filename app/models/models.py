from pydantic import BaseModel
from typing import List

class Place(BaseModel):
    Location: str
    Nearest_City: str
    Distance_from_Nearest_City_km: float
    Travel_Time_to_Location_hr: float
    Entry_fee_LKR: float
    Travel_Method_Suitable: List[str]
    Travel_Method_Low_Budget: List[str]
    Travel_Guide_needed: int
    Activity_Tools_Needed: int
    Category_Waterfalls_Lakes: int
    Category_History: int
    Category_Nature: int
    Category_Adventure: int
    Category_Beaches: int
    Category_Religious_Spiritual: int
    Category_National_Parks_Wildlife: int
    Category_Hiking_Mountain: int
    Category_Gardens_Botanical: int
    Category_Urban_City: int
    Category_Ayurveda_Wellness: int
    Category_Water_Sports: int
    Latitude: float
    Longitude: float
    score: int

class Plan(BaseModel):
    places: List[Place]

class PlanResponse(BaseModel):
    plan: List[Plan]
