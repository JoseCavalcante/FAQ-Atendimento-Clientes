# 🏦 Atendimento & Suporte IA — SaaS Platform

Plataforma SaaS (Software as a Service) B2B inteligente para atendimento e suporte ao cliente. Este projeto utiliza **LLMs** (Large Language Models) e **RAG** (Retrieval-Augmented Generation) para responder perguntas de forma segura e com base exclusiva em documentos internos de cada empresa.

## 🌟 Principais Funcionalidades

- **🏛️ Multi-Tenancy Segura**: Separação completa de dados (banco de dados e vetorial) por empresa (Tenant). Usuários de uma empresa nunca acessam documentos de outra.
- **🔐 Autenticação JWT**: Login e cadastro seguros. O acesso às rotas da API é protegido e exige tokens de acesso válidos.
- **📄 Gestão de Documentos (RAG)**: Upload de PDFs, processamento automático, particionamento de texto e conversão em *Embeddings* salvos no ChromaDB.
- **💬 Chat Inteligente com Fontes**: O assistente responde perguntas buscando no banco vetorial da empresa e retorna não apenas a resposta, mas também citações das páginas que serviram de base.
- **💳 Controle de Billing (Assinaturas)**: Sistema de planos (Free, Pro, Enterprise) com limites de perguntas por mês, quantidade de usuários e tamanho máximo de arquivos.
- **🖥️ Dashboard Moderno**: Uma interface web estilo "Single Page Application" (SPA) completa, com Dark Mode, design *Glassmorphism* e atualizações em tempo real.

## 🛠️ Tecnologias Utilizadas

**Backend:**
- [Python 3.10+](https://www.python.org/)
- [FastAPI](https://fastapi.tiangolo.com/) (API Assíncrona e Roteamento)
- [SQLAlchemy](https://www.sqlalchemy.org/) (ORM para banco de dados relacional)
- [ChromaDB](https://www.trychroma.com/) (Banco de dados vetorial local)
- [LangChain](https://www.langchain.com/) (Orquestração de Prompts e RAG)
- [Groq](https://groq.com/) + Llama 3.3 70B (Inferência de IA ultrarrápida)
- Passlib, Bcrypt e Python-Jose (Criptografia e JWT)

**Frontend:**
- HTML5 Semântico
- Vanilla CSS3 (Design Responsivo, Variáveis CSS)
- Vanilla JavaScript (Fetch API, manipulação de DOM)

## 🏗️ Estrutura do Projeto

```text
BackEnd_AtendimentoSuporte/
├── api/v1/                # Rotas da API REST (Chat, Documentos, Tenant)
├── auth/                  # Lógica de Autenticação, Dependências e JWT
├── database/              # Conexão SQL, Modelos SQLAlchemy e ChromaDB
├── Service/               # Regras de Negócio (LLM, Embeddings, Billing)
├── static/                # Arquivos do Frontend (HTML, CSS, JS)
├── uploads/               # Armazenamento de PDFs
├── config.py              # Configurações globais e de Planos (SaaS)
├── main.py                # Ponto de entrada do servidor Uvicorn
├── requirements.txt       # Dependências do Python
└── .env                   # Variáveis de ambiente
```

## 🚀 Instalação e Execução

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd BackEnd_AtendimentoSuporte
```

### 2. Criar e ativar o ambiente virtual

```powershell
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto contendo as seguintes chaves essenciais:

```env
GROQ_API_KEY=sua_chave_groq_aqui
JWT_SECRET=uma_chave_secreta_aleatoria_super_segura
```

*(O banco de dados relacional será gerado automaticamente num arquivo `saas.db` na raiz)*

### 5. Iniciar o Servidor

```bash
python -m uvicorn main:app --reload
```

### 6. Acessar a Plataforma
Abra o navegador e acesse a interface do sistema:
👉 **[http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)**


