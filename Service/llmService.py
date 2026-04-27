import os
from pathlib import Path
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models import BaseChatModel

class LLMService:
    """
    Serviço para interação com LLMs usando LangChain e Groq.
    """

    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """
        Inicializa o serviço LLM.

        Args:
            model_name: Nome do modelo a ser usado no Groq.
            temperature: Temperatura para geração (0.0 a 1.0).
            max_tokens: Limite máximo de tokens na resposta.
            timeout: Tempo limite em segundos para a requisição.
        """
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY não encontrada no arquivo .env")

        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._llm: Optional[BaseChatModel] = None

    @property
    def llm(self) -> BaseChatModel:
        """
        Retorna a instância do LLM, criando-a se necessário (Lazy Loading).
        """
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def _create_llm(self) -> BaseChatModel:
        """
        Cria e configura a instância do ChatGroq.
        """
        return ChatGroq(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            max_retries=2,
            api_key=self.api_key
        )

    def get_response(self, question: str, context: str) -> str:
        """
        Gera uma resposta baseada em uma pergunta e um contexto fornecido.

        Args:
            question: A pergunta do usuário.
            context: O contexto recuperado (ex: texto de PDF) para basear a resposta.

        Returns:
            A resposta gerada pelo LLM.
        """
        template = """
        Responda à pergunta usando apenas as informações do contexto fornecido abaixo.
        Se a resposta não estiver no contexto, diga gentilmente que não possui essa informação.

        Contexto:
        {context}

        Pergunta:
        {question}
        """

        prompt = PromptTemplate.from_template(template)
        chain = prompt | self.llm | StrOutputParser()

        response = chain.invoke({
            "context": context,
            "question": question
        })

        return response

    @staticmethod
    def get_document_path(filename: str = "manual-safebank.pdf") -> Path:
        """
        Retorna o caminho absoluto para um arquivo de documento.
        """
        current_dir = Path(__file__).resolve().parent
        # Assume que a pasta 'docs' está no nível raiz do projeto, pai de 'Service'
        return current_dir.parent / "docs" / filename


if __name__ == "__main__":
    # Teste simples da classe
    try:
        service = LLMService()
        
        # Define paths
        doc_path = service.get_document_path()
        print(f"Caminho do documento: {doc_path}")

        # Exemplo de uso (RAG Simulado)
        contexto_exemplo = """
        O SafeBank oferece isenção de taxas para clientes com investimentos acima de R$ 50.000,00.
        Para abrir uma conta, é necessário documento com foto e comprovante de residência.
        """
        pergunta = "Quais os requisitos para abrir uma conta?"
        
        print("\n--- Teste de Geração ---")
        resposta = service.get_response(pergunta, contexto_exemplo)
        print(f"P: {pergunta}")
        print(f"R: {resposta}")

    except Exception as e:
        print(f"Erro durante a execução do teste: {e}")


