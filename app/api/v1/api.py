from fastapi import APIRouter
from app.api.v1.endpoints import trips

api_router = APIRouter()
api_router.include_router(trips.router, prefix="/trips", tags=["Trips & Planning"])