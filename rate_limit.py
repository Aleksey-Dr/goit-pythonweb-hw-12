# rate_limit.py

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)

def init_rate_limit(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class RateLimitExceeded(Exception):
    pass

@limiter.limit("5/minute")
async def limit_user_me(request: Request, response: Response):
    return True
