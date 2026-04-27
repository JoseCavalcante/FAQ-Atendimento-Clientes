# Análise Completa do Projeto (SaaS B2B de IA)

O projeto **Atendimento & Suporte IA** é uma plataforma SaaS (Software as a Service) completa focada em B2B (Business-to-Business). Ele permite que empresas façam o upload de seus documentos internos e interajam com eles através de um chat inteligente baseado em LLMs.

## 🏗 Arquitetura e Tecnologias

- **Backend:** Python com **FastAPI** (alta performance, assíncrono).
- **Banco de Dados Relacional:** SQLAlchemy assíncrono, atualmente usando **SQLite** (`saas.db`), preparado para escalar para PostgreSQL facilmente.
- **Banco de Dados Vetorial:** **ChromaDB** (`chroma_data/`) para busca semântica (RAG).
- **Inteligência Artificial:** **LangChain** para orquestração de Prompts/RAG e a API do **Groq** rodando o modelo open-source **Llama-3.3-70b**.
- **Frontend:** Vanilla JavaScript, HTML5 e CSS3 (sem frameworks pesados), construído no formato SPA (Single Page Application).

---

## 📂 Estrutura de Diretórios e Módulos

### 1. Módulo Core (`main.py` & `config.py`)
- **`main.py`**: O ponto de entrada da aplicação. Configura o FastAPI, inicializa o banco de dados e engloba todas as rotas (Routers).
- **`config.py`**: Gerencia variáveis de ambiente e define as **regras de negócio de Billing** (limites de queries, preços dos planos, tamanho máximo de upload, etc).

### 2. Módulo de Autenticação (`auth/`)
- Gerencia o isolamento de informações. Quando um usuário se cadastra, ele cria uma entidade `Tenant` (Empresa).
- Utiliza **JWT (JSON Web Tokens)** para proteger as rotas da API, garantindo que usuários só acessem dados da própria organização.

### 3. Módulo de Serviços (`Service/`)
A lógica de negócio pesada fica isolada aqui (Service Pattern):
- **`llmService.py`**: Conecta-se ao Groq usando LangChain para gerar as respostas.
- **`embeddingService.py`**: Processa PDFs, "fatia" o texto (chunks) e converte em embeddings.
- **`documentService.py`**: Gerencia o upload físico dos arquivos na pasta `storage/` ou `uploads/`.
- **`billingService.py` & `usageService.py`**: Validam se a empresa pode fazer upgrades de plano e contabilizam o uso (ex: bloqueia perguntas se o plano Free esgotar).

### 4. Módulo de Rotas da API (`api/v1/`)
- **`document_router.py`**: Recebe uploads, deleta arquivos e lista os PDFs da empresa logada.
- **`chat_router.py`**: Recebe a pergunta do usuário, busca no banco vetorial (RAG) e devolve a resposta gerada. Também salva o histórico no banco de dados.
- **`tenant_router.py`**: Devolve os dados para alimentar o Dashboard (uso de recursos, informações do plano).

### 5. Frontend (`static/`)
- Uma interface limpa, com design moderno ("Glassmorphism", Dark Mode).
- O arquivo `app.js` cuida de toda a mudança de telas (Login -> Chat -> Documentos -> Dashboard) sem precisar recarregar a página.

---

## ⚙️ O Fluxo Principal (RAG Pipeline)

A mágica da plataforma se concentra no RAG (Retrieval-Augmented Generation):

1. **Ingestão (Upload):** O usuário envia um PDF. O arquivo é salvo localmente.
2. **Processamento:** O `embeddingService` lê o PDF usando o `PyPDFLoader`, recorta o texto a cada ~1000 caracteres, gera os vetores matemáticos e os guarda no ChromaDB, amarrando tudo ao ID da Empresa (`tenant_id`).
3. **Busca (Retrieval):** O usuário faz uma pergunta no chat. O sistema busca no ChromaDB os 5 trechos de texto mais semelhantes matematicamente à pergunta daquele usuário.
4. **Geração (Generation):** Os trechos de texto (junto com a pergunta) são mandados para a IA, que é estritamente orientada por prompt a responder **somente** usando aqueles textos, evitando alucinações.
5. **Apresentação:** O frontend exibe a resposta da IA acompanhada das referências (número da página lida).

---

## 📈 Potencial e Próximos Passos
O projeto já está estruturalmente pronto para produção. Como melhorias futuras (escalabilidade), a plataforma está preparada para:
- Trocar o SQLite por um banco de dados **PostgreSQL**.
- Substituir o armazenamento de arquivos local por **AWS S3**.
- Adicionar a biblioteca Stripe no `billingService` para processar pagamentos reais com cartão de crédito na tela de Upgrade.
