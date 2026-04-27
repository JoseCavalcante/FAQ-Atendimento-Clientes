"""
Serviço de autenticação: registro, login, JWT tokens, hashing.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.models import User, Tenant

settings = get_settings()

# ── Password Hashing ──
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT Tokens ──
def create_access_token(user_id: str, extra: dict = None) -> str:
    """Cria um JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Cria um JWT refresh token (longa duração)."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica um JWT token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])





def slugify(text: str) -> str:
    """Converte texto para slug (lowercase, sem espaços, sem acentos)."""
    import unicodedata
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    return text


# ── Operações de Banco ──
async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    company_name: str,
) -> dict:
    """
    Registra um novo usuário + cria o Tenant (organização).
    O primeiro usuário é admin do tenant.
    """

    # Verificar se email já existe
    result = await db.execute(select(User).where(User.email == email.lower()))
    if result.scalar_one_or_none():
        raise ValueError("Este email já está cadastrado.")

    # Criar slug único para o tenant
    base_slug = slugify(company_name)
    slug = base_slug
    counter = 1
    while True:
        result = await db.execute(select(Tenant).where(Tenant.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Criar Tenant
    tenant = Tenant(
        name=company_name,
        slug=slug,
        plan="free",
    )
    db.add(tenant)
    await db.flush()  # Gera o ID do tenant

    # Criar User (admin do tenant)
    user = User(
        tenant_id=tenant.id,
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=full_name,
        role="admin",
    )
    db.add(user)
    await db.flush()

    # Gerar tokens
    access_token = create_access_token(user.id, {"tenant_id": tenant.id, "role": user.role})
    refresh_token = create_refresh_token(user.id)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def login_user(db: AsyncSession, email: str, password: str) -> dict:
    """Autentica um usuário e retorna tokens JWT."""
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise ValueError("Email ou senha incorretos.")

    if not user.is_active:
        raise ValueError("Conta desativada. Entre em contato com o suporte.")

    # Verificar se o tenant está ativo
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant or not tenant.is_active:
        raise ValueError("Organização desativada.")

    # Atualizar último login
    user.last_login = datetime.now(timezone.utc)

    # Gerar tokens
    access_token = create_access_token(user.id, {"tenant_id": tenant.id, "role": user.role})
    refresh_token = create_refresh_token(user.id)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict:
    """Renova o access token usando um refresh token válido."""
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Token inválido — não é um refresh token.")
    except Exception:
        raise ValueError("Refresh token inválido ou expirado.")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise ValueError("Usuário não encontrado.")

    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()

    new_access = create_access_token(user.id, {"tenant_id": tenant.id, "role": user.role})

    return {
        "access_token": new_access,
        "token_type": "bearer",
    }
