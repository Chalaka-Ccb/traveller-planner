import httpx
from app.core.config import settings
from typing import List, Tuple

# ORS API base URL
ORS_BASE_URL = "https://api.openrouteservice.org"

def get_coordinates_for_location(location_name: str) -> Tuple[float, float] | None:
    """
    Uses ORS Geocoding to find the coordinates for a location name.
    Returns (longitude, latitude) or None.
    """
    client = httpx.Client()
    try:
        response = client.get(
            f"{ORS_BASE_URL}/geocode/search",
            params={
                "api_key": settings.ORS_API_KEY,
                "text": location_name,
                "boundary.country": "LKA", # Restrict search to Sri Lanka
                "size": 1
            }
        )
        response.raise_for_status() # Raise error for bad responses (4xx, 5xx)
        data = response.json()
        
        if data.get("features"):
            # Coordinates are [longitude, latitude]
            coords = data["features"][0]["geometry"]["coordinates"]
            return (coords[0], coords[1])
        return None
    except httpx.HTTPStatusError as e:
        print(f"HTTP error during geocoding: {e}")
        return None
    except Exception as e:
        print(f"Error in get_coordinates_for_location: {e}")
        return None
    finally:
        client.close()

def get_distance_matrix(locations: List[Tuple[float, float]]) -> dict | None:
    """
    Gets a distance/duration matrix from ORS for a list of coordinates.
    The coordinates must be in (longitude, latitude) format.
    """
    client = httpx.Client()
    headers = {
        'Authorization': settings.ORS_API_KEY,
        'Content-Type': 'application/json'
    }
    body = {
        "locations": locations,
        "metrics": ["duration"], # You can also ask for 'distance'
        "units": "km"
    }
    
    try:
        response = client.post(
            f"{ORS_BASE_URL}/v2/matrix/driving-car",
            json=body,
            headers=headers
        )
        response.raise_for_status() # This will catch 4xx/5xx errors
        return response.json()
    except httpx.HTTPStatusError as e:
        # This will catch errors like the 400 Bad Request you saw before
        print(f"FATAL ERROR in get_distance_matrix: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        print(f"Error in get_distance_matrix: {e}")
        return None
    finally:
        client.close()