"""Supabase client initialization and management."""

import logging
from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings

logger = logging.getLogger(__name__)

REQUIRED_BUCKETS = ["resumes", "recordings", "materials"]


def _ensure_storage_buckets(client: Client) -> None:
    """Create required storage buckets if they don't already exist."""
    try:
        existing = client.storage.list_buckets()
        existing_names = {b.name for b in existing}
    except Exception as e:
        logger.warning("Could not list storage buckets: %s", e)
        return

    for bucket_name in REQUIRED_BUCKETS:
        if bucket_name not in existing_names:
            try:
                client.storage.create_bucket(bucket_name, options={"public": False})
                logger.info("Created storage bucket: %s", bucket_name)
            except Exception as e:
                # Bucket may have been created concurrently
                logger.warning("Could not create bucket '%s': %s", bucket_name, e)


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
    _ensure_storage_buckets(client)
    return client
