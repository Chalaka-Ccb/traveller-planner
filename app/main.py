from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.api import itinerary

app = FastAPI(title="SmartTravelLK API", version="0.1.0", debug=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(itinerary.router)

@app.get("/")
def root():
    return {"message": "SmartTravelLK API is running"}


