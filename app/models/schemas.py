from pydantic import BaseModel, EmailStr
from typing import List, Optional

# --- Trip Generation (Screenshot 1) ---

class TripGenerationRequest(BaseModel):
    num_people: int
    num_days: int
    budget: float
    interests: List[str] # e.g., ["nature", "history"]
    # You can add these later:
    # meal_options: bool = False
    # accommodation_options: bool = False

class LocationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    image_url: Optional[str]
    coordinates: dict # {"longitude": 79.8, "latitude": 7.1}

class TripDayResponse(BaseModel):
    day_number: int
    locations: List[LocationResponse]

class TripResponse(BaseModel):
    id: str
    num_people: int
    num_days: int
    total_budget: float
    itinerary: List[TripDayResponse]

# --- Reservation (Screenshot 4) ---

class ReservationRequest(BaseModel):
    trip_id: str # The ID of the generated trip they are booking
    first_name: str
    last_name: str
    email: EmailStr
    address: Optional[str]
    post_code: Optional[str]
    country: Optional[str]
    mobile_phone: Optional[str]
    passport_number: str # The non-editable unique ID

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str

    class Config:
        from_attributes = True # <-- New name