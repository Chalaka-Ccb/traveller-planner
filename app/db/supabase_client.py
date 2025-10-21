from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    """
    Initializes and returns a Supabase client.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be set in .env file")
        
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return supabase

# Create a single instance to be used by the app
supabase_client = get_supabase_client()