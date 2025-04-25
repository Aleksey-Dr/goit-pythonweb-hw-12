# cors.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def enable_cors(app: FastAPI):
    """
    Enables Cross-Origin Resource Sharing (CORS) for the FastAPI application.

    This function adds the CORSMiddleware to the application, allowing requests
    from different origins. It is configured to allow all origins, credentials,
    methods, and headers. **Note:** In a production environment, you should
    restrict the `allow_origins` to specific trusted domains for security.

    Args:
        app (FastAPI): The FastAPI application instance to which CORS will be added.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all sources (for development)
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
