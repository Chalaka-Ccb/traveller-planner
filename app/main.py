from fastapi import FastAPI
from app.api.v1.api import api_router

app = FastAPI(
    title="Sri Lanka Travel Planner API",
    description="Backend service for the smart travel planning application.",
    version="1.0.0"
)

# Include the v1 router
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Health"])
def read_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"status": "ok", "message": "Welcome to the Travel Planner API!"}

# To run the app, save this and in your terminal run:
# uvicorn app.main:app --reload