from pathlib import Path
import re
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


class DocumentLoaderService:
    """
    Serviço responsável por carregar e normalizar documentos PDF
    """

    def __init__(self, docs_path: Path):
        if not docs_path.exists():
            raise FileNotFoundError(f"Pasta de documentos não encontrada: {docs_path}")

        self.docs_path = docs_path


    def load_pdf(self, filename: str) -> List[Document]:
        """
        Carrega um PDF e retorna uma lista de Document (uma por página)
        """
        pdf_path = self.docs_path / filename

        if not pdf_path.exists():
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")

        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()        
        return documents

    def load_first_page(self, filename: str) -> Document:
        """
        Carrega apenas a primeira página de um PDF
        """
        documents = self.load_pdf(filename)
        return documents[0]

    
    def normalize_text(self, list_pages: List[Document]) -> List[Document]:
        normalized_documents = []

        for page in list_pages:
            text = page.page_content

            text = re.sub(r"\n+", "\n", text)
            text = re.sub(r"\s+", " ", text)
            text = text.strip()

            normalized_documents.append(
                Document(
                    page_content=text,
                    metadata=page.metadata
                )
            )
        
        return normalized_documents