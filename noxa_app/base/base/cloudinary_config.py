import cloudinary
import os

def configure_cloudinary():
    """Configure Cloudinary with credentials"""
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', 'dsupmimkx'),
        api_key=os.environ.get('CLOUDINARY_API_KEY', '732974968223895'),
        api_secret= os.environ.get('CLOUDINARY_API_SECRET'),
        secure=True
    )
    return cloudinary.config()