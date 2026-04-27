"""
Serviço de gestão de documentos (upload, listagem, remoção).
"""

from pathlib import Path
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from database.models import Document, Tenant
from storage.file_storage import FileStorage, get_storage
from config import get_settings

settings = get_settings()


class DocumentService:
    """CRUD de documentos por tenant."""

    def __init__(self, storage: FileStorage = None):
        self.storage = storage or get_storage()

    async def upload(
        self,
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
        file: UploadFile,
    ) -> Document:
        """
        Upload de um documento PDF.
        Valida limites do plano antes de aceitar.
        """
        # 1. Validar tipo de arquivo
        if not file.filename.lower().endswith(".pdf"):
            raise ValueError("Apenas arquivos PDF são aceitos.")

        # 2. Ler conteúdo para verificar tamanho
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # Reset para salvar depois

        # 3. Verificar limites do plano
        tenant = await db.get(Tenant, tenant_id)
        plan_config = settings.PLANS.get(tenant.plan, settings.PLANS["free"])

        max_size = plan_config["max_file_size_mb"] * 1024 * 1024
        if file_size > max_size:
            raise ValueError(
                f"Arquivo muito grande ({file_size / 1024 / 1024:.1f} MB). "
                f"Limite do plano {plan_config['name']}: {plan_config['max_file_size_mb']} MB."
            )

        # 4. Verificar quantidade de documentos
        max_docs = plan_config["max_documents"]
        if max_docs > 0:
            result = await db.execute(
                select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
            )
            current_count = result.scalar()
            if current_count >= max_docs:
                raise ValueError(
                    f"Limite de documentos atingido ({max_docs}). "
                    f"Faça upgrade do plano para enviar mais."
                )

        # 5. Verificar duplicata
        result = await db.execute(
            select(Document).where(
                Document.tenant_id == tenant_id,
                Document.original_name == file.filename,
            )
        )
        if result.scalar_one_or_none():
            raise ValueError(f"Já existe um documento com o nome '{file.filename}'.")

        # 6. Salvar arquivo no storage
        safe_filename = self.storage.generate_filename(file.filename)
        path = await self.storage.save(file.file, tenant_id, safe_filename)

        # 7. Contar páginas do PDF
        page_count = await self._count_pdf_pages(content)

        # 8. Criar registro no banco
        document = Document(
            tenant_id=tenant_id,
            uploaded_by=user_id,
            filename=safe_filename,
            original_name=file.filename,
            file_size=file_size,
            page_count=page_count,
        )
        db.add(document)
        await db.flush()

        return document

    async def list_documents(
        self,
        db: AsyncSession,
        tenant_id: str,
    ) -> List[Document]:
        """Lista todos os documentos de um tenant."""
        result = await db.execute(
            select(Document)
            .where(Document.tenant_id == tenant_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_document(
        self,
        db: AsyncSession,
        tenant_id: str,
        document_id: str,
    ) -> Optional[Document]:
        """Retorna um documento específico do tenant."""
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_document(
        self,
        db: AsyncSession,
        tenant_id: str,
        document_id: str,
    ) -> bool:
        """Remove um documento (arquivo + registro)."""
        document = await self.get_document(db, tenant_id, document_id)
        if not document:
            return False

        # Remover arquivo do storage
        path = f"{tenant_id}/{document.filename}"
        await self.storage.delete(path)

        # Remover do banco
        await db.delete(document)
        return True

    async def get_document_path(
        self,
        db: AsyncSession,
        tenant_id: str,
        document_id: str,
    ) -> Optional[str]:
        """Retorna o caminho completo do arquivo no storage."""
        document = await self.get_document(db, tenant_id, document_id)
        if not document:
            return None
        path = f"{tenant_id}/{document.filename}"
        return await self.storage.get_full_path(path)

    @staticmethod
    async def _count_pdf_pages(content: bytes) -> int:
        """Conta páginas de um PDF a partir de bytes."""
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(content))
            return len(reader.pages)
        except Exception:
            return 0
