"""
Serviço de embedding e vetorização de documentos.
Pipeline: PDF → Texto → Chunks → Embeddings → Vector Store.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import get_settings
from database.vector_store import VectorStore

settings = get_settings()


class EmbeddingService:
    """Processa documentos para busca vetorial."""

    def __init__(self):
        self.vector_store = VectorStore()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def process_document(
        self,
        file_path: str,
        tenant_id: str,
        document_id: str,
    ) -> int:
        """
        Pipeline completo: carrega PDF, divide em chunks, armazena no vector store.
        Retorna quantidade de chunks criados.

        Esta é uma operação síncrona (CPU-bound) — deve ser executada em thread pool.
        """
        # 1. Carregar PDF
        loader = PyPDFLoader(file_path)
        pages = loader.load()

        # 2. Normalizar texto de cada página
        for page in pages:
            page.page_content = self._normalize_text(page.page_content)

        # 3. Dividir em chunks
        chunks = self.text_splitter.split_documents(pages)

        # Filtrar chunks vazios ou muito curtos
        chunks = [c for c in chunks if len(c.page_content.strip()) > 50]

        if not chunks:
            return 0

        # 4. Preparar dados para o vector store
        texts = [chunk.page_content for chunk in chunks]
        metadatas = [
            {
                "document_id": document_id,
                "page": chunk.metadata.get("page", 0),
                "source": chunk.metadata.get("source", ""),
            }
            for chunk in chunks
        ]

        # 5. Remover chunks antigos deste documento (re-processamento)
        self.vector_store.delete_document_chunks(tenant_id, document_id)

        # 6. Adicionar ao vector store (ChromaDB gera embeddings)
        count = self.vector_store.add_chunks(
            tenant_id=tenant_id,
            document_id=document_id,
            chunks=texts,
            metadatas=metadatas,
        )

        return count

    def search_context(
        self,
        tenant_id: str,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Busca contexto relevante no vector store.
        Retorna os chunks mais similares à query.
        """
        return self.vector_store.search(
            tenant_id=tenant_id,
            query=query,
            top_k=top_k,
            document_id=document_id,
        )

    def build_context_from_results(self, results: List[Dict]) -> str:
        """
        Monta o contexto textual a partir dos resultados da busca vetorial.
        """
        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results):
            page = result.get("metadata", {}).get("page", "?")
            content = result["content"]
            distance = result.get("distance", 0)
            context_parts.append(
                f"[Trecho {i + 1} | Página {int(page) + 1} | Relevância: {1 - distance:.0%}]\n{content}"
            )

        return "\n\n---\n\n".join(context_parts)

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Remove espaços e quebras de linha excessivas."""
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()
