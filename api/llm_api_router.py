import asyncio
from functools import partial
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from Service.llmService import LLMService
from Service.pdfService import DocumentLoaderService

# --- Routers ---
# Router público: rotas consumidas pelo frontend (sem API Key)
router_public = APIRouter()

# Router protegido: rotas que exigem API Key
router_protected = APIRouter()

# --- Instanciação dos serviços ---
llm_service = LLMService()

DOCS_PATH = Path(__file__).resolve().parent.parent / "docs"
document_loader_service = DocumentLoaderService(DOCS_PATH)

# Limite seguro de caracteres para contexto (~100K chars ≈ ~25K tokens)
MAX_CONTEXT_CHARS = 100_000


@router_public.get("/llm/docs", summary="Listar documentos disponíveis")
async def list_available_docs():
    """
    Lista todos os arquivos PDF disponíveis na pasta docs/ para uso no RAG.
    """
    try:
        pdf_files = sorted([
            {
                "filename": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1)
            }
            for f in DOCS_PATH.iterdir()
            if f.suffix.lower() == ".pdf"
        ], key=lambda x: x["filename"])

        return {"total": len(pdf_files), "documents": pdf_files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_protected.post("/llm", summary="Consultar LLM com contexto manual")
async def ask_llm(
    question: str = Query(..., description="A pergunta do usuário"),
    context: str = Query(..., description="O contexto para basear a resposta")
):
    """
    Envia uma pergunta ao LLM com um contexto fornecido manualmente.
    """
    try:
        # Validar tamanho do contexto
        if len(context) > MAX_CONTEXT_CHARS:
            raise HTTPException(
                status_code=400,
                detail=f"Contexto muito grande ({len(context):,} chars). Limite: {MAX_CONTEXT_CHARS:,} chars."
            )

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            partial(llm_service.get_response, question, context)
        )
        return {"response": response}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_public.post("/llm/rag", summary="Consultar LLM com RAG (PDF automático)")
async def ask_llm_rag(
    question: str = Query(..., description="A pergunta do usuário"),
    filename: str = Query("manual-safebank.pdf", description="Nome do PDF na pasta docs"),
    max_pages: Optional[int] = Query(None, description="Limite de páginas como contexto (vazio = todas)")
):
    """
    Carrega um PDF, normaliza o conteúdo e usa como contexto para responder via LLM.
    """
    try:
        loop = asyncio.get_running_loop()

        # 1. Carregar o PDF
        documents = await loop.run_in_executor(
            None,
            partial(document_loader_service.load_pdf, filename)
        )

        # 2. Normalizar o texto
        normalized = document_loader_service.normalize_text(documents)

        # 3. Limitar páginas se solicitado
        if max_pages and max_pages > 0:
            normalized = normalized[:max_pages]

        # 4. Montar o contexto a partir das páginas
        context = "\n\n".join(
            f"[Página {doc.metadata.get('page', i) + 1}]\n{doc.page_content}"
            for i, doc in enumerate(normalized)
        )

        # 5. Validar tamanho do contexto
        if len(context) > MAX_CONTEXT_CHARS:
            # Truncar o contexto ao limite seguro com aviso
            context = context[:MAX_CONTEXT_CHARS]

        # 6. Enviar ao LLM
        response = await loop.run_in_executor(
            None,
            partial(llm_service.get_response, question, context)
        )

        return {
            "response": response,
            "filename": filename,
            "pages_used": len(normalized)
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))