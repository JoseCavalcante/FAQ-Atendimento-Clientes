"""
Conexão com o banco de dados usando SQLAlchemy Async.
Suporta SQLite (dev) e PostgreSQL (produção) via DATABASE_URL.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

settings = get_settings()

# ── Engine ──
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    # SQLite precisa de check_same_thread=False
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

# ── Session Factory ──
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base Model ──
class Base(DeclarativeBase):
    pass


# ── Dependency para injetar session nas rotas ──
async def get_db() -> AsyncSession:
    """
    Dependency do FastAPI que fornece uma sessão do banco.
    Uso: db: AsyncSession = Depends(get_db)
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Criar tabelas (dev only — em produção usar Alembic) ──
async def create_tables():
    """Cria todas as tabelas no banco. Usar apenas em desenvolvimento."""
    async with engine.begin() as conn:
        from database.models import (  # noqa: F401 — importar para registrar modelos
            Tenant, User, Document, Conversation, Message
        )
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Remove todas as tabelas. CUIDADO: perda de dados!"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
