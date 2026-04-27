import asyncio
from functools import partial
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from Service.pdfService import DocumentLoaderService

router = APIRouter()

# Caminho da pasta de documentos (relativo à raiz do projeto)
DOCS_PATH = Path(__file__).resolve().parent.parent / "docs"
document_loader_service = DocumentLoaderService(DOCS_PATH)


def _serialize_metadata(metadata: dict) -> Dict[str, Any]:
    """Converte valores não serializáveis (ex: Path) para string."""
    return {k: str(v) if isinstance(v, Path) else v for k, v in metadata.items()}


def _format_pages(documents) -> List[Dict[str, Any]]:
    """Formata lista de Document para resposta JSON."""
    return [
        {
            "page_content": doc.page_content,
            "metadata": _serialize_metadata(doc.metadata)
        }
        for doc in documents
    ]


@router.post("/pdf/load", summary="Carregar PDF")
async def load_pdf(
    filename: str = Query(..., description="Nome do arquivo PDF na pasta docs")
):
    """
    Carrega um PDF da pasta docs e retorna o conteúdo de todas as páginas.
    """
    try:
        loop = asyncio.get_running_loop()
        documents = await loop.run_in_executor(
            None,
            partial(document_loader_service.load_pdf, filename)
        )
        pages = _format_pages(documents)
        return {"total_pages": len(pages), "pages": pages}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pdf/normalize", summary="Carregar e normalizar PDF")
async def load_and_normalize_pdf(
    filename: str = Query(..., description="Nome do arquivo PDF na pasta docs")
):
    """
    Carrega um PDF e retorna o conteúdo normalizado (sem espaços/quebras excessivas).
    """
    try:
        loop = asyncio.get_running_loop()
        documents = await loop.run_in_executor(
            None,
            partial(document_loader_service.load_pdf, filename)
        )
        normalized = document_loader_service.normalize_text(documents)
        pages = _format_pages(normalized)
        return {"total_pages": len(pages), "pages": pages}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))