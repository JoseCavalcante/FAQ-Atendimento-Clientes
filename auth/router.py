"""
Rotas de autenticação: registro, login, refresh, perfil.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth.service import register_user, login_user, refresh_access_token
from auth.dependencies import get_current_user
from database.connection import get_db
from database.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Request/Response Schemas ──
class RegisterRequest(BaseModel):
    email: str = Field(..., description="Email do usuário")
    password: str = Field(..., description="Senha")
    full_name: str = Field(..., description="Nome completo")
    company_name: str = Field(..., description="Nome da empresa/organização")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email do usuário")
    password: str = Field(..., description="Senha")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token JWT")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: dict
    tenant: dict


# ── Endpoints ──
@router.post("/register", response_model=TokenResponse, status_code=201, summary="Registrar novo usuário")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Cria uma nova conta de usuário e organização (tenant).
    O primeiro usuário é automaticamente admin.
    """
    try:
        result = await register_user(
            db=db,
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            company_name=body.company_name,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse, summary="Login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Autentica um usuário e retorna tokens JWT (access + refresh).
    """
    try:
        result = await login_user(db=db, email=body.email, password=body.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", summary="Renovar token")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Renova o access token usando um refresh token válido.
    """
    try:
        result = await refresh_access_token(db=db, refresh_token=body.refresh_token)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", summary="Dados do usuário logado")
async def get_me(user: User = Depends(get_current_user)):
    """
    Retorna os dados do usuário autenticado.
    """
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }
