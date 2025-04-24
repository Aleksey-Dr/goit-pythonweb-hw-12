# cors.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def enable_cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all sources (for development)
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
