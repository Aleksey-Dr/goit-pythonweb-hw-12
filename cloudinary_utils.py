# cloudinary_utils.py

import os
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)
"""
Configuration for the Cloudinary service.

This configuration is loaded from environment variables for the cloud name, API key, and API secret.
Ensure these environment variables are set for the Cloudinary integration to work.
"""

async def upload_avatar(base64_image: str):
    """
    Asynchronously uploads a base64 encoded image to Cloudinary.

    Args:
        base64_image (str): A string containing the base64 encoded image data.

    Returns:
        Optional[str]: The URL of the uploaded image on Cloudinary if successful, otherwise None.
    """
    try:
        upload_result = cloudinary.uploader.upload(base64_image)
        return upload_result.get("url")
    except Exception as e:
        print(f"Error uploading to Cloudinary: {e}")
        return None
    