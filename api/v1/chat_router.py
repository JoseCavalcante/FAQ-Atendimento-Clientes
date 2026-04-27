"""
Rotas de chat RAG com vector store (SaaS).
Autenticação obrigatória, isolamento por tenant.
"""

import asyncio
from functools import partial
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user, get_current_tenant
from database.connection import get_db
from database.models import User, Tenant, Document, Conversation, Message
from Service.llmService import LLMService
from Service.embeddingService import EmbeddingService
from Service.documentService import DocumentService

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])

llm_service = LLMService()
embedding_service = EmbeddingService()
doc_service = DocumentService()


# ── Schemas ──
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="Pergunta do usuário")
    document_id: Optional[str] = Field(None, description="ID do documento para busca (opcional)")
    conversation_id: Optional[str] = Field(None, description="ID da conversa existente (opcional)")
    top_k: int = Field(5, ge=1, le=20, description="Quantidade de trechos de contexto")


class ProcessDocumentRequest(BaseModel):
    document_id: str = Field(..., description="ID do documento para processar")


# ── Chat RAG ──
@router.post("", summary="Enviar pergunta (RAG)")
async def chat_rag(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Envia uma pergunta que é respondida usando RAG (busca vetorial + LLM).
    Se document_id for fornecido, busca apenas naquele documento.
    """
    # 1. Verificar limites de uso
    plan_config = settings.PLANS.get(tenant.plan, settings.PLANS["free"])
    max_queries = plan_config["max_queries_per_month"]
    if max_queries > 0 and tenant.queries_this_month >= max_queries:
        raise HTTPException(
            status_code=429,
            detail=f"Limite mensal de consultas atingido ({max_queries}). Faça upgrade do plano."
        )

    # 2. Validar document_id se fornecido
    if body.document_id:
        doc = await doc_service.get_document(db, tenant.id, body.document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Documento não encontrado.")
        if not doc.is_processed:
            raise HTTPException(
                status_code=400,
                detail="Documento ainda não foi processado. Use POST /api/v1/chat/process primeiro."
            )

    # 3. Buscar contexto no vector store
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(
        None,
        partial(
            embedding_service.search_context,
            tenant_id=tenant.id,
            query=body.question,
            document_id=body.document_id,
            top_k=body.top_k,
        ),
    )

    if not results:
        raise HTTPException(
            status_code=404,
            detail="Nenhum contexto relevante encontrado. Verifique se há documentos processados."
        )

    context = embedding_service.build_context_from_results(results)

    # 4. Gerar resposta via LLM
    response_text = await loop.run_in_executor(
        None,
        partial(llm_service.get_response, body.question, context),
    )

    # 5. Salvar conversa e mensagens
    conversation_id = body.conversation_id

    if not conversation_id:
        # Criar nova conversa
        conversation = Conversation(
            tenant_id=tenant.id,
            user_id=user.id,
            title=body.question[:100],
            document_id=body.document_id,
        )
        db.add(conversation)
        await db.flush()
        conversation_id = conversation.id

    # Salvar mensagem do usuário
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=body.question,
    )
    db.add(user_msg)

    # Salvar resposta do assistente
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=response_text,
    )
    db.add(assistant_msg)

    # 6. Incrementar contador de uso
    tenant.queries_this_month += 1

    return {
        "response": response_text,
        "conversation_id": conversation_id,
        "sources": [
            {
                "page": r.get("metadata", {}).get("page", 0) + 1,
                "relevance": round((1 - r.get("distance", 0)) * 100, 1),
                "preview": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],
            }
            for r in results
        ],
        "usage": {
            "queries_this_month": tenant.queries_this_month,
            "max_queries": max_queries,
        },
    }


# ── Processar Documento (Vetorizar) ──
@router.post("/process", summary="Processar documento para RAG")
async def process_document(
    body: ProcessDocumentRequest,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Processa um documento PDF: extrai texto, divide em chunks e armazena no vector store.
    Necessário antes de usar o documento no chat RAG.
    """
    document = await doc_service.get_document(db, tenant.id, body.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    # Obter caminho do arquivo
    file_path = await doc_service.get_document_path(db, tenant.id, body.document_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no storage.")

    # Processar em thread pool (operação pesada)
    loop = asyncio.get_running_loop()
    try:
        chunk_count = await loop.run_in_executor(
            None,
            partial(
                embedding_service.process_document,
                file_path=file_path,
                tenant_id=tenant.id,
                document_id=document.id,
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar documento: {str(e)}")

    # Atualizar status no banco
    from datetime import datetime, timezone
    document.is_processed = True
    document.chunk_count = chunk_count
    document.processed_at = datetime.now(timezone.utc)

    return {
        "document_id": document.id,
        "original_name": document.original_name,
        "chunk_count": chunk_count,
        "status": "processed",
    }


# ── Histórico de Conversas ──
@router.get("/conversations", summary="Listar conversas")
async def list_conversations(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Lista todas as conversas do usuário."""
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id,
        )
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    return {
        "total": len(conversations),
        "conversations": [
            {
                "id": conv.id,
                "title": conv.title,
                "document_id": conv.document_id,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            }
            for conv in conversations
        ],
    }


@router.get("/conversations/{conversation_id}", summary="Mensagens de uma conversa")
async def get_conversation_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Retorna todas as mensagens de uma conversa."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant.id,
            Conversation.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()

    return {
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
        },
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    }


# Importar settings no escopo do módulo
from config import get_settings
settings = get_settings()
