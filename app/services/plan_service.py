# File: app/services/plan_service.py

from supabase import Client
from app.models.schemas import TripGenerationRequest, TripResponse, LocationResponse, TripDayResponse
from app.core.config import settings
from app.services import ors_service
from fastapi import HTTPException
from typing import List, Dict, Any

# Import the client instance directly
from app.db.supabase_client import supabase_client as db_client

# Helper function to parse PostGIS point "POINT(lon lat)"
def parse_point_string(point_str: str) -> Dict[str, float]:
    try:
        # Removes "POINT(" and ")" and splits "lon lat"
        lon, lat = point_str.strip("POINT()").split()
        return {"longitude": float(lon), "latitude": float(lat)}
    except Exception:
        # Return default or raise error if parsing fails
        print(f"Error parsing point string: {point_str}")
        # Depending on requirements, you might want to handle this differently
        # For now, return 0,0 - but this could lead to bad data if not caught
        return {"longitude": 0.0, "latitude": 0.0}

def generate_trip_plan(request: TripGenerationRequest) -> TripResponse:

    # 1. Budget Check
    min_budget = settings.DAILY_BUDGET_PER_PERSON * request.num_people * request.num_days
    if request.budget < min_budget:
        raise HTTPException(
            status_code=400,
            detail=f"Budget is too low. Minimum required budget for {request.num_people} people for {request.num_days} days is ${min_budget}."
        )

    # 2. Fetch locations from Supabase matching ANY of the interests
    try:
        locations_response = db_client.rpc(
            'get_locations_by_tags',
            {'tag_names': request.interests}
        ).execute()

        if not locations_response.data:
            raise HTTPException(status_code=404, detail="No locations found matching your interests.")

        all_locations = locations_response.data
    except Exception as e:
        print(f"Supabase error fetching locations: {e}") # Keep detailed logging
        raise HTTPException(status_code=500, detail="Error fetching locations from database.")

    # 3. Prioritize locations
    interest_set = set(request.interests)
    perfect_matches = []
    partial_matches = []

    for loc in all_locations:
        loc_tags = set(loc['tags'])
        # Ensure 'lon' and 'lat' exist and are not None before appending
        if 'lon' in loc and 'lat' in loc and loc['lon'] is not None and loc['lat'] is not None:
             if interest_set.issubset(loc_tags):
                 perfect_matches.append(loc)
             else:
                 partial_matches.append(loc)
        else:
            print(f"Warning: Location {loc.get('name', 'Unknown')} missing coordinates, skipping.")


    # Final sorted list: perfect matches first, then partial matches
    sorted_locations = perfect_matches + partial_matches

    # Check if we have any valid locations after filtering
    if not sorted_locations:
         raise HTTPException(status_code=404, detail="No valid locations with coordinates found for your interests.")

    # --- 4. Build the Itinerary (Greedy Nearest-Neighbor Algorithm) ---
    itinerary_days = [] # <--- Initialization happens here
    available_locations = sorted_locations.copy()

    # Start at the airport
    current_coords = settings.STARTING_POINT_COORDS

    for day_num in range(1, request.num_days + 1):
        day_plan_locations = []

        # 5. Assign up to 6 locations per day
        for _ in range(6):
            if not available_locations:
                break # Stop if we run out of locations

            # Prepare coordinates for ORS Matrix API
            # First location is our current spot, the rest are destinations
            # Ensure coordinates are valid floats
            try:
                coord_list = [current_coords] + [
                    (float(loc['lon']), float(loc['lat'])) for loc in available_locations
                ]
            except (ValueError, KeyError, TypeError) as coord_err:
                 print(f"Error preparing coordinates for ORS: {coord_err}. Skipping day planning step.")
                 # Decide how to handle this - skip step, skip day, or raise error?
                 # For now, let's break the inner loop for this day
                 break


            # Get the distance matrix
            matrix = ors_service.get_distance_matrix(coord_list)

            # Defensive check for matrix structure
            if not matrix or 'durations' not in matrix or not matrix['durations'] or not matrix['durations'][0]:
                print(f"ORS Matrix API failed or returned unexpected structure: {matrix}. Breaking plan generation.")
                # Clear available locations to stop outer loop gracefully or raise specific error
                available_locations = []
                break # Break inner loop (locations for the day)

            # 'durations[0]' gives travel times FROM our current_coords (index 0)
            # TO all other locations (index 1 onwards)
            travel_times = matrix['durations'][0][1:]

            # Ensure travel_times has the same length as available_locations
            if len(travel_times) != len(available_locations):
                print(f"Mismatch between travel times ({len(travel_times)}) and available locations ({len(available_locations)}). Skipping step.")
                # This could happen if ORS couldn't route to some points.
                # Simplest recovery: break the inner loop for the day.
                break


            if not travel_times:
                print("No travel times returned by ORS. Stopping day planning.")
                break # No routes found for remaining locations from current point

            # Find the index of the closest location based on duration
            closest_index = min(range(len(travel_times)), key=lambda i: travel_times[i] if travel_times[i] is not None else float('inf'))

            # Check if a valid closest location was found (ORS might return None for unreachable points)
            if travel_times[closest_index] is None:
                 print(f"Could not find a route to any remaining locations from {current_coords}. Stopping day planning.")
                 break


            # Get the chosen location (and remove it safely)
            chosen_location = available_locations.pop(closest_index)
            day_plan_locations.append(chosen_location)

            # Update the current location coordinates
            current_coords = (float(chosen_location['lon']), float(chosen_location['lat']))


        # Add the day's plan to the itinerary IF any locations were added
        if day_plan_locations:
            itinerary_days.append(
                TripDayResponse(
                    day_number=day_num,
                    locations=[
                        LocationResponse(
                            id=loc['id'],
                            name=loc['name'],
                            description=loc['description'],
                            image_url=loc['image_url'],
                            coordinates={"longitude": float(loc['lon']), "latitude": float(loc['lat'])}
                        ) for loc in day_plan_locations
                    ]
                )
            )

        # If we broke out of the inner loop due to ORS failure or no locations left, stop building days
        if not available_locations:
            break

    # Check if ANY itinerary days were generated
    if not itinerary_days:
        raise HTTPException(status_code=404, detail="Could not generate any valid itinerary days with the selected locations and routing.")

    # 6. Save the new trip to the database
    new_trip_id = None # Initialize variables outside try block
    new_trip = None
    try:
        trip_insert_response = db_client.table('trips').insert({
            "num_people": request.num_people,
            "num_days": request.num_days, # Use requested num_days, even if itinerary is shorter
            "total_budget": request.budget
        }).execute()

        # Check if insert was successful and data exists
        if not trip_insert_response.data:
             raise Exception("Failed to insert trip into database or no data returned.")

        new_trip = trip_insert_response.data[0]
        new_trip_id = new_trip['id']

        # Prepare batch insert for all trip days
        trip_days_data = []
        for day in itinerary_days: # Uses itinerary_days, which is guaranteed to exist here
            for i, loc in enumerate(day.locations):
                 # Ensure location ID is valid before appending
                 if loc.id:
                    trip_days_data.append({
                        "trip_id": new_trip_id,
                        "day_number": day.day_number,
                        "step_order": i + 1,
                        "location_id": loc.id
                    })
                 else:
                     print(f"Warning: Location {loc.name} has invalid ID on Day {day.day_number}, skipping.")


        # Only insert trip_days if there's data to insert
        if trip_days_data:
             days_insert_response = db_client.table('trip_days').insert(trip_days_data).execute()
             # Optional: Check days_insert_response for errors
             if not days_insert_response.data and len(trip_days_data) > 0: # Check if insert might have failed
                  print("Warning: Trip days insert command executed but returned no data.")
        else:
             print("Warning: No valid trip day locations to save.")


    except Exception as e:
        print(f"Supabase error saving trip: {e}") # Keep detailed logging
        # If saving fails, we might want to clean up the trip entry if it was partially created
        # For now, just raise the error
        raise HTTPException(status_code=500, detail="Failed to save the generated trip.")

    # Ensure new_trip_id and new_trip are valid before returning
    if not new_trip_id or not new_trip:
         # This should theoretically not happen if the try block succeeded without error
         # but serves as a safeguard.
         print("Error: Trip ID or Trip data is missing after supposedly successful save.")
         raise HTTPException(status_code=500, detail="Internal error after saving trip.")


    # 7. Return the full trip plan
    return TripResponse(
        id=new_trip_id,
        num_people=new_trip['num_people'],
        num_days=new_trip['num_days'], # Return the num_days from the saved trip record
        total_budget=new_trip['total_budget'],
        itinerary=itinerary_days # Uses itinerary_days, which exists here
    )