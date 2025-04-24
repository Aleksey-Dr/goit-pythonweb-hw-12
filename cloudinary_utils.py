# cloudinary_utils.py

import os
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

async def upload_avatar(base64_image: str):
    try:
        upload_result = cloudinary.uploader.upload(base64_image)
        return upload_result.get("url")
    except Exception as e:
        print(f"Error uploading to Cloudinary: {e}")
        return None
    