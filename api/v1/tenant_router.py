"""
Rotas de configurações do tenant (plano, uso, billing).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user, get_current_tenant, require_admin
from database.connection import get_db
from database.models import User, Tenant
from Service.usageService import UsageService
from Service.billingService import BillingService

router = APIRouter(prefix="/api/v1/tenant", tags=["Tenant"])

usage_service = UsageService()
billing_service = BillingService()


# ── Schemas ──
class UpgradePlanRequest(BaseModel):
    plan: str = Field(..., description="Slug do novo plano: free, pro, enterprise")


# ── Endpoints ──
@router.get("/info", summary="Informações do tenant")
async def get_tenant_info(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Retorna informações do tenant e do usuário logado."""
    return {
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at.isoformat(),
        },
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@router.get("/usage", summary="Uso atual do tenant")
async def get_usage(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Retorna o uso atual comparado com os limites do plano."""
    return await usage_service.get_usage(db, tenant.id)


@router.get("/plans", summary="Listar planos disponíveis")
async def list_plans():
    """Retorna todos os planos disponíveis com seus recursos."""
    return {"plans": billing_service.get_plans()}


@router.post("/upgrade", summary="Atualizar plano")
async def upgrade_plan(
    body: UpgradePlanRequest,
    user: User = Depends(require_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Atualiza o plano do tenant. Apenas admins podem fazer upgrade.
    Em produção, integra com Stripe para processamento de pagamento.
    """
    try:
        result = await billing_service.upgrade_plan(db, tenant.id, body.plan)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
