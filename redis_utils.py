# redis_utils.py

import os
import redis

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
"""
Global Redis client instance.

This client is configured using environment variables for host, port, and database.
It automatically decodes responses from Redis as strings.
"""

async def get_redis():
    """
    Asynchronous dependency to provide the global Redis client.

    Returns:
        redis.Redis: The configured Redis client instance.
    """
    return redis_client
