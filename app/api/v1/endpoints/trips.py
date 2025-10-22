# File: app/api/v1/endpoints/trips.py

from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import TripGenerationRequest, TripResponse, ReservationRequest, UserResponse
from app.db.supabase_client import supabase_client # Keep this if reserve-trip uses it
from app.services import plan_service
from supabase import Client # Keep type hint if reserve-trip uses it

router = APIRouter()

# Dependency (Keep if /reserve-trip needs it, otherwise remove)
def get_db():
    return supabase_client

# --- REMOVE 'db: Client = Depends(get_db)' ---
@router.post("/generate-plan", response_model=TripResponse)
def generate_plan(
    request: TripGenerationRequest
):
    """
    Generates a new personalized travel plan based on user inputs.
    """
    try:
        # --- REMOVE 'db' ARGUMENT FROM CALL ---
        trip_plan = plan_service.generate_trip_plan(request)
        return trip_plan
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error in /generate-plan: {e}") # Keep detailed logging
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

# --- Make similar changes to /reserve-trip if needed ---
@router.post("/reserve-trip", response_model=UserResponse)
def reserve_trip(
    request: ReservationRequest,
    db: Client = Depends(get_db) # Keep this for now
):
    # This endpoint still uses the injected 'db'
    # If you change plan_service globally, you might want to change this too
    # For now, let's focus on fixing generate_plan
    try:
        user_response = db.table('users').upsert({ # uses injected db
           # ... user data ...
        }, on_conflict='email').execute()

        new_user = user_response.data[0]

        db.table('trips').update({ # uses injected db
            'user_id': new_user['id']
        }).eq('id', request.trip_id).execute()

        return UserResponse.from_orm(new_user)

    except Exception as e:
        # ... error handling ...
        print(f"Error in /reserve-trip: {e}")
        raise HTTPException(status_code=500, detail="Could not process reservation.")