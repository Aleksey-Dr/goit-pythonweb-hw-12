# tests/test_cors.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from starlette.testclient import TestClient

from cors import enable_cors


def test_enable_cors_no_origin_header():
    """
    Tests the behavior when the Origin header is not present in the request.
    CORS headers might not be present in this case.
    """
    app = FastAPI()
    enable_cors(app)
    client = TestClient(app)

    @app.get("/no_origin")
    async def no_origin_endpoint():
        return {"message": "No Origin header test"}

    response = client.get("/no_origin")
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers