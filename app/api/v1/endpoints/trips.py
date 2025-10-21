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


# app/api/v1/endpoints/trips.py
#
# from fastapi import APIRouter, Depends, HTTPException, status  # <-- Import status
# from app.models.schemas import TripGenerationRequest, TripResponse, ReservationRequest, UserResponse
# from app.db.supabase_client import supabase_client
# from app.services import plan_service
# from supabase import Client
#
# # +++ Import the new dependency function +++
# from app.auth.clerk_auth import get_current_user_id
#
# # +++++++++++++++++++++++++++++++++++++++++++
#
# router = APIRouter()
#
#
# # Dependency to get Supabase client (still needed for reserve_trip)
# def get_db():
#     return supabase_client
#
#
# # --- /generate-plan remains unchanged (no auth required) ---
# @router.post("/generate-plan", response_model=TripResponse)
# def generate_plan(
#         request: TripGenerationRequest
# ):
#     """
#     Generates a new personalized travel plan based on user inputs. (Public)
#     """
#     try:
#         trip_plan = plan_service.generate_trip_plan(request)
#         return trip_plan
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         print(f"Unexpected error in /generate-plan: {e}")
#         raise HTTPException(status_code=500, detail="An internal server error occurred.")
#
#
# # --- /reserve-trip now requires authentication ---
# @router.post("/reserve-trip", response_model=UserResponse)
# async def reserve_trip(  # <-- Make endpoint async if dependency is async
#         request: ReservationRequest,
#         db: Client = Depends(get_db),
#         # +++ Add the authentication dependency HERE +++
#         current_user_clerk_id: str = Depends(get_current_user_id)
#         # ++++++++++++++++++++++++++++++++++++++++++++++
# ):
#     """
#     Saves user details for a generated trip. Requires authentication.
#     """
#     print(f"Reservation request received for Clerk User ID: {current_user_clerk_id}")
#
#     # Optional: Check if a user with this Clerk ID already exists in your `users` table
#     # This depends on whether you store Clerk IDs in your `users` table.
#     # If not, you might need to adjust your user creation/linking logic.
#
#     # For now, let's assume the request includes all needed info (like passport)
#     # and we link the trip to the user record created/updated via the request details.
#     # A more robust approach might be to create/find the user based on clerk ID
#     # and only *then* update their details and link the trip.
#
#     try:
#         # Upsert user based on email or passport
#         user_response = db.table('users').upsert({
#             'email': request.email,
#             'first_name': request.first_name,
#             'last_name': request.last_name,
#             'address': request.address,
#             'post_code': request.post_code,
#             'country': request.country,
#             'mobile_phone': request.mobile_phone,
#             'passport_number': request.passport_number
#             # Consider adding a 'clerk_user_id' column to your 'users' table
#             # and setting it here: 'clerk_user_id': current_user_clerk_id
#         }, on_conflict='email').execute()  # Or on_conflict='passport_number' if email isn't unique enough
#
#         if not user_response.data:
#             raise Exception("User upsert failed or returned no data.")
#
#         db_user = user_response.data[0]
#         db_user_id = db_user['id']  # Get the UUID from your database
#
#         # Link the trip to the user in your database
#         trip_update_response = db.table('trips').update({
#             'user_id': db_user_id  # Link using your internal DB user ID
#         }).eq('id', request.trip_id).execute()
#
#         # Optional: Check trip_update_response for errors or if rows were updated
#
#         # Return user details from your database record
#         return UserResponse.model_validate(db_user)  # Use model_validate in Pydantic v2
#
#     except Exception as e:
#         # Handle unique constraint violation (e.g., passport_number exists for different email)
#         if 'violates unique constraint' in str(e):
#             raise HTTPException(
#                 status_code=status.HTTP_409_CONFLICT,
#                 detail="A user with this email or passport number might already exist."
#             )
#         print(f"Error in /reserve-trip: {e}")
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not process reservation.")