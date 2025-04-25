# rate_limit.py

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)

def init_rate_limit(app: FastAPI):
    """
    Initializes the rate limiting middleware for the FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class RateLimitExceeded(Exception):
    """
    Custom exception raised when a rate limit is exceeded.
    """
    pass

@limiter.limit("5/minute")
async def limit_user_me(request: Request, response: Response):
    """
    Example rate-limited endpoint dependency.

    This function applies a rate limit of 5 requests per minute to the endpoint it is used in.
    If the limit is exceeded, a `RateLimitExceeded` exception will be raised.

    Args:
        request (Request): The incoming FastAPI request object.
        response (Response): The outgoing FastAPI response object.

    Returns:
        bool: Always returns True if the request is within the rate limit.
              Raises a `RateLimitExceeded` exception otherwise.
    """
    return True
