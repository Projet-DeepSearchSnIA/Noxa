import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
region = os.getenv('AWS_REGION', 'eu-north-1')
bucket_name = os.getenv('BUCKET_NAME', 'nlp-rag-bucket')


s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=region
)

# get a pre-signed url for a pdf
def get_signed_url(s3_key, expiration=3600):
    """Generate a presigned URL for private S3 objects"""
     
    try:
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": bucket_name, 
                "Key": s3_key,  # ex: documents/memoires/monfichier.pdf
            },
            ExpiresIn=expiration,  
        )
        return url
    except Exception as e:
        print(f"Error generating signed URL: {e}")
        return None


def upload_file_to_s3(file, s3_path, public=True):
    """
    Upload a file to AWS S3 and return the file URL.
    
    :param file: Django UploadedFile object to upload
    :param s3_path: Destination path in S3 (example: 'subjects/2025/math.pdf')
    :param public: If True, file will be public, otherwise private
    """

    # Validate bucket_name
    if not bucket_name or not isinstance(bucket_name, str):
        print(f"Invalid bucket_name: {bucket_name} (type: {type(bucket_name)})")
        return None

    try:
        # Reset file pointer to beginning
        file.seek(0)
        
        extra_args = {
            # "ACL": "public-read" if public else "private",
            "ContentType": file.content_type  # Important for PDFs
        }

        # Upload file - use file.file to get the file object
        
        s3.upload_fileobj(
            file.file if hasattr(file, 'file') else file,
            bucket_name,
            s3_path,
            ExtraArgs=extra_args
        )

        # Public URL (only works if ACL = public-read)
        if public:
            url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_path}"
            return url
        else:
            # If private, return a signed URL
            return get_signed_url(s3_path)

    except NoCredentialsError:
        print("AWS credentials not found!")
        return None
    except ClientError as e:
        print(f"Failed to upload file: {e}")
        return None
    except Exception as e:
        print(f"Something happened: {e}")
        import traceback
        traceback.print_exc()  # for more details
        return None
    


########################################################################
########################################################################
########################################################################

### USE OF CLOUDINARY ##########

def upload_file_cloudinary(file_type="image", file=None, public_id=None, folder=None, **kwargs):
    """
    Upload a file to Cloudinary and return the URL.
    
    :param file_type: 'image' or 'raw' (for PDFs, etc.)
    :param file: Django UploadedFile object to upload
    :param public_id: Custom public ID for the file (optional)
    :param folder: Folder path in Cloudinary (optional)
    :param kwargs: Additional parameters for Cloudinary uploader
    :return: URL of the uploaded file or None
    """
    import cloudinary.uploader

    try:
        # Prepare upload options
        upload_options = {
            "resource_type": file_type,
            "public_id": public_id,
            "folder": folder,
            "access_mode": "public",
            **kwargs
        }

        # Remove None values
        upload_options = {k: v for k, v in upload_options.items() if v is not None}

        # Upload file
        if file:
            upload_result = cloudinary.uploader.upload(file, **upload_options)
        else:
            # If no file provided, you might want to handle that case
            raise ValueError("No file provided for upload")

        # Return the secure URL
        return upload_result.get("secure_url")

    except Exception as e:
        print(f"Cloudinary upload failed: {e}")
        return None


