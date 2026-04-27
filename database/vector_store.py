"""
Wrapper para o Vector Store (ChromaDB).
Gerencia collections por tenant para isolamento de dados.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional

from config import get_settings, CHROMA_DIR

settings = get_settings()

# ── ChromaDB Client (persistente em disco) ──
_chroma_client = None


def get_chroma_client() -> chromadb.ClientAPI:
    """Retorna o cliente ChromaDB (singleton)."""
    global _chroma_client
    if _chroma_client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def _collection_name(tenant_id: str) -> str:
    """Gera nome da collection para um tenant."""
    # ChromaDB exige nomes com 3-63 chars, alfanumérico + underscore
    safe_id = tenant_id.replace("-", "")[:32]
    return f"t_{safe_id}"


class VectorStore:
    """Interface para operações de vector store por tenant."""

    def __init__(self):
        self.client = get_chroma_client()

    def get_collection(self, tenant_id: str):
        """Obtém ou cria a collection do tenant."""
        name = _collection_name(tenant_id)
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        tenant_id: str,
        document_id: str,
        chunks: List[str],
        metadatas: List[Dict] = None,
        embeddings: List[List[float]] = None,
    ) -> int:
        """
        Adiciona chunks de um documento ao vector store.
        Retorna a quantidade de chunks adicionados.
        """
        collection = self.get_collection(tenant_id)

        ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]

        if metadatas is None:
            metadatas = [
                {"document_id": document_id, "chunk_index": i}
                for i in range(len(chunks))
            ]
        else:
            # Garantir que document_id está em todos os metadatas
            for i, meta in enumerate(metadatas):
                meta["document_id"] = document_id
                meta["chunk_index"] = i

        if embeddings:
            collection.add(
                ids=ids,
                documents=chunks,
                metadatas=metadatas,
                embeddings=embeddings,
            )
        else:
            # ChromaDB gera embeddings automaticamente com modelo default
            collection.add(
                ids=ids,
                documents=chunks,
                metadatas=metadatas,
            )

        return len(chunks)

    def search(
        self,
        tenant_id: str,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        query_embedding: List[float] = None,
    ) -> List[Dict]:
        """
        Busca por similaridade no vector store.
        Pode filtrar por document_id específico.
        """
        collection = self.get_collection(tenant_id)

        where_filter = None
        if document_id:
            where_filter = {"document_id": document_id}

        if query_embedding:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
            )
        else:
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter,
            )

        # Formatar resultados
        formatted = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                formatted.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                    "id": results["ids"][0][i] if results["ids"] else "",
                })

        return formatted

    def delete_document_chunks(self, tenant_id: str, document_id: str) -> None:
        """Remove todos os chunks de um documento do vector store."""
        collection = self.get_collection(tenant_id)
        # Buscar IDs dos chunks do documento
        try:
            results = collection.get(
                where={"document_id": document_id},
            )
            if results and results["ids"]:
                collection.delete(ids=results["ids"])
        except Exception:
            pass  # Collection pode não existir ainda

    def delete_tenant_collection(self, tenant_id: str) -> None:
        """Remove toda a collection de um tenant."""
        name = _collection_name(tenant_id)
        try:
            self.client.delete_collection(name=name)
        except Exception:
            pass

    def get_collection_stats(self, tenant_id: str) -> Dict:
        """Retorna estatísticas da collection do tenant."""
        collection = self.get_collection(tenant_id)
        return {
            "name": collection.name,
            "count": collection.count(),
        }
