"""Supabase client initialization and management."""

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Get cached Supabase client instance.

    Returns:
        Configured Supabase client using service role key
        for server-side operations.
    """
    settings = get_settings()
    client: Client = create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_role_key,
    )
    return client
