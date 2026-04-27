"""
Rotas de gestão de documentos (upload, listagem, remoção).
Todas as rotas exigem autenticação e são isoladas por tenant.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user, get_current_tenant
from database.connection import get_db
from database.models import User, Tenant
from Service.documentService import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

doc_service = DocumentService()


@router.post("", status_code=201, summary="Upload de documento PDF")
async def upload_document(
    file: UploadFile = File(..., description="Arquivo PDF para upload"),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Faz upload de um documento PDF para o tenant do usuário autenticado.
    Valida limites do plano (tamanho, quantidade).
    """
    try:
        document = await doc_service.upload(
            db=db,
            tenant_id=tenant.id,
            user_id=user.id,
            file=file,
        )
        return {
            "id": document.id,
            "original_name": document.original_name,
            "file_size": document.file_size,
            "page_count": document.page_count,
            "is_processed": document.is_processed,
            "created_at": document.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", summary="Listar documentos")
async def list_documents(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os documentos do tenant."""
    documents = await doc_service.list_documents(db, tenant.id)
    return {
        "total": len(documents),
        "documents": [
            {
                "id": doc.id,
                "original_name": doc.original_name,
                "file_size": doc.file_size,
                "file_size_kb": round(doc.file_size / 1024, 1),
                "page_count": doc.page_count,
                "is_processed": doc.is_processed,
                "chunk_count": doc.chunk_count,
                "created_at": doc.created_at.isoformat(),
            }
            for doc in documents
        ],
    }


@router.get("/{document_id}", summary="Detalhes de um documento")
async def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Retorna detalhes de um documento específico."""
    document = await doc_service.get_document(db, tenant.id, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return {
        "id": document.id,
        "original_name": document.original_name,
        "file_size": document.file_size,
        "page_count": document.page_count,
        "is_processed": document.is_processed,
        "chunk_count": document.chunk_count,
        "created_at": document.created_at.isoformat(),
        "processed_at": document.processed_at.isoformat() if document.processed_at else None,
    }


@router.delete("/{document_id}", status_code=204, summary="Remover documento")
async def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Remove um documento e seu arquivo do storage."""
    deleted = await doc_service.delete_document(db, tenant.id, document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return None
