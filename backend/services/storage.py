"""Class to store whole files in gcs"""
from config import BUCKET_NAME
import logging
from google.cloud import storage

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.gcs_client = storage.Client()
        self.gcs_bucket_name = BUCKET_NAME
        try:
            self.gcs_bucket = self.gcs_client.get_bucket(self.gcs_bucket_name)
            logger.info(f"Using existing bucket: {self.gcs_bucket_name}")
        except Exception as e:
            logger.error(f"Error accessing bucket ({self.gcs_bucket_name}): {e}")
            raise
    
    def upload_file(self, filename: str, content: bytes):
        try:
            blob = self.gcs_bucket.blob(filename)
            if blob.exists():
                logger.info(f"File: {filename} already stored in gcs")
                return f"gs://{self.gcs_bucket_name}/{filename}"
            
            blob.upload_from_string(content)    # works with bytes
            gcs_uri = f"gs://{self.gcs_bucket_name}/{filename}"
            logger.info(f"file {filename} uploaded to GCS")
            return gcs_uri
        except Exception as e:
            logger.error(f"Failed to upload file {filename} to gcs: {e}", exc_info=True)
            raise
