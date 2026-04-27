"""
Atendimento & Suporte IA — SaaS API
FastAPI application com multi-tenancy, autenticação JWT e RAG.
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import APIKeyHeader

""" from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded """

from config import get_settings, STATIC_DIR, UPLOADS_DIR

settings = get_settings()


# ── Lifespan: inicializar banco de dados ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos ao iniciar e limpa ao encerrar."""
    # Startup
    from database.connection import create_tables
    await create_tables()

    # Criar diretórios necessários
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"✅ {settings.APP_NAME} v{settings.APP_VERSION} iniciado")
    print(f"📦 Database: {settings.DATABASE_URL.split('///')[-1] if 'sqlite' in settings.DATABASE_URL else 'PostgreSQL'}")
    print(f"📂 Uploads: {UPLOADS_DIR}")

    yield

    # Shutdown
    print("🛑 Encerrando aplicação...")


# ── Rate Limiter (Desativado por falta de dependência) ──
# limiter = Limiter(key_func=get_remote_address)

# ── App ──
app = FastAPI(
    title=settings.APP_NAME,
    description="Plataforma SaaS de atendimento ao cliente com IA, RAG e multi-tenancy.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Import Routers ──
# Rotas legadas (compatibilidade)
from api.api_App import router as app_router
from api.llm_api_router import router_public as llm_public_router
from api.llm_api_router import router_protected as llm_protected_router
from api.pdf_api_router import router as pdf_router

# Rotas SaaS v1
from auth.router import router as auth_router
from api.v1.document_router import router as doc_router
from api.v1.chat_router import router as chat_router
from api.v1.tenant_router import router as tenant_router

# ── API Key Auth (para rotas legadas) ──
API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verifica API Key (rotas legadas). Desativada se API_KEY vazia."""
    if not API_KEY:
        return None
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida.")
    return api_key


# ── Registrar Routers ──

# 1. Rotas públicas (app)
app.include_router(app_router, tags=["App"])

# 2. Auth (registro, login, refresh, perfil)
app.include_router(auth_router)

# 3. SaaS v1 (autenticação JWT — via dependencies internas dos routers)
app.include_router(doc_router)
app.include_router(chat_router)
app.include_router(tenant_router)

# 4. Rotas legadas do LLM (público: docs list, RAG)
app.include_router(llm_public_router, tags=["LLM (Legacy)"])

# 5. Rotas legadas protegidas por API Key
app.include_router(
    llm_protected_router,
    tags=["LLM (Legacy)"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    pdf_router,
    tags=["PDF (Legacy)"],
    dependencies=[Depends(verify_api_key)],
)

# ── Servir arquivos estáticos ──
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Frontend ──
@app.get("/app", summary="Frontend do Assistente", include_in_schema=False)
async def serve_frontend():
    """Serve a página principal do frontend."""
    return FileResponse(str(STATIC_DIR / "index.html"))