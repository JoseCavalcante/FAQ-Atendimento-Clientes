"""
Abstração de armazenamento de arquivos.
Suporta Local (dev) e S3 (produção).
"""

import os
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from config import get_settings, UPLOADS_DIR

settings = get_settings()


class FileStorage(ABC):
    """Interface para armazenamento de arquivos."""

    @abstractmethod
    async def save(self, file_data: BinaryIO, tenant_id: str, filename: str) -> str:
        """Salva um arquivo e retorna o path relativo."""
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Remove um arquivo pelo path."""
        ...

    @abstractmethod
    async def get_full_path(self, path: str) -> str:
        """Retorna o caminho completo para leitura."""
        ...

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Verifica se o arquivo existe."""
        ...

    @staticmethod
    def generate_filename(original_name: str) -> str:
        """Gera um nome de arquivo único preservando a extensão."""
        ext = Path(original_name).suffix
        return f"{uuid.uuid4().hex}{ext}"


class LocalStorage(FileStorage):
    """Armazenamento local em disco."""

    def __init__(self, base_dir: Path = UPLOADS_DIR):
        self.base_dir = base_dir

    async def save(self, file_data: BinaryIO, tenant_id: str, filename: str) -> str:
        """Salva arquivo em uploads/{tenant_id}/{filename}"""
        tenant_dir = self.base_dir / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)

        file_path = tenant_dir / filename
        with open(file_path, "wb") as f:
            # Ler em chunks para não sobrecarregar memória
            while chunk := file_data.read(8192):
                f.write(chunk)

        # Retorna path relativo
        return f"{tenant_id}/{filename}"

    async def delete(self, path: str) -> None:
        full_path = self.base_dir / path
        if full_path.exists():
            full_path.unlink()

    async def get_full_path(self, path: str) -> str:
        return str(self.base_dir / path)

    async def exists(self, path: str) -> bool:
        return (self.base_dir / path).exists()


class S3Storage(FileStorage):
    """Armazenamento em AWS S3. Requer boto3."""

    def __init__(self):
        try:
            import boto3
            self.s3 = boto3.client("s3", region_name=settings.S3_REGION)
            self.bucket = settings.S3_BUCKET
        except ImportError:
            raise RuntimeError("boto3 não instalado. Execute: pip install boto3")

    async def save(self, file_data: BinaryIO, tenant_id: str, filename: str) -> str:
        key = f"{tenant_id}/{filename}"
        self.s3.upload_fileobj(file_data, self.bucket, key)
        return key

    async def delete(self, path: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=path)

    async def get_full_path(self, path: str) -> str:
        url = self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": path},
            ExpiresIn=3600,
        )
        return url

    async def exists(self, path: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=path)
            return True
        except Exception:
            return False


def get_storage() -> FileStorage:
    """Factory: retorna o storage configurado."""
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalStorage()
