# storage.py
import os
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile


class StorageService:
    """
    Service to handle file uploads to S3 or Azure Blob Storage.
    Falls back to local storage if cloud credentials are not configured.
    """

    def __init__(self):
        self.storage_type = self._detect_storage_type()

    def _detect_storage_type(self) -> str:
        """Detect which storage backend to use based on environment variables."""
        if all(
            [
                os.getenv("AWS_ACCESS_KEY_ID"),
                os.getenv("AWS_SECRET_ACCESS_KEY"),
                os.getenv("AWS_S3_BUCKET_NAME"),
            ]
        ):
            return "s3"
        elif all(
            [
                os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
                os.getenv("AZURE_STORAGE_CONTAINER_NAME"),
            ]
        ):
            return "azure"
        else:
            return "local"

    async def upload_file(
        self, file: UploadFile, folder: str = "uploads"
    ) -> Optional[str]:
        """
        Upload file to configured storage backend.

        Args:
            file: The file to upload
            folder: The folder/prefix for organizing files

        Returns:
            The URL or path to the uploaded file
        """
        #if self.storage_type == "s3":
        #    return await self._upload_to_s3(file, folder)
        #elif self.storage_type == "azure":

        return await self._upload_to_azure(file, folder)
        #else:
        #   return await self._upload_to_local(file, folder)

    async def _upload_to_s3(self, file: UploadFile, folder: str) -> str:
        """Upload file to AWS S3."""
        try:
            import boto3
            from pathlib import Path

            s3_client = boto3.client(
                "s3",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )

            bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
            ext = Path(file.filename).suffix
            file_name = f"{folder}/{uuid4().hex}{ext}"

            # Upload file to S3
            s3_client.upload_fileobj(
                file.file,
                bucket_name,
                file_name,
                ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
            )

            # Return the S3 URL
            region = os.getenv("AWS_REGION", "us-east-1")
            return f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_name}"

        except ImportError:
            raise Exception(
                "boto3 is not installed. Install it with: pip install boto3"
            )
        except Exception as e:
            raise Exception(f"Failed to upload to S3: {str(e)}")

    async def _upload_to_azure(self, file: UploadFile, folder: str) -> str:
        try:
            import os
            from uuid import uuid4
            from pathlib import Path

            from azure.storage.blob import BlobServiceClient, ContentSettings

            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")

            if not connection_string or not container_name:
                raise Exception("Missing AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_CONTAINER_NAME")

            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            container_client = blob_service_client.get_container_client(container_name)

            ext = Path(file.filename).suffix
            blob_name = f"{folder}/{uuid4().hex}{ext}"

            blob_client = container_client.get_blob_client(blob_name)

            # ⚠️ Importante: el puntero del archivo puede no estar al inicio
            file.file.seek(0)

            blob_client.upload_blob(
                data=file.file,
                overwrite=True,
                content_settings=ContentSettings(
                    content_type=file.content_type or "application/octet-stream"
                ),
            )

            return blob_client.url

        except ImportError:
            raise Exception(
                "azure-storage-blob is not installed. Install it with: pip install azure-storage-blob"
            )
        except Exception as e:
            raise Exception(f"Failed to upload to Azure: {str(e)}")

    async def _upload_to_local(self, file: UploadFile, folder: str) -> str:
        """Upload file to local filesystem (fallback)."""
        import shutil
        from pathlib import Path

        uploads_dir = Path(folder)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(file.filename).suffix
        file_name = f"{uuid4().hex}{ext}"
        file_path = uploads_dir / file_name

        with file_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        return str(file_path)


# Singleton instance
storage_service = StorageService()
