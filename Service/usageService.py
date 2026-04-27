"""
Serviço de tracking de uso por tenant.
Controla limites de queries, documentos e storage.
"""

from datetime import datetime, timezone
from typing import Dict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.models import Tenant, Document, Message

settings = get_settings()


class UsageService:
    """Monitora e aplica limites de uso por tenant."""

    async def get_usage(self, db: AsyncSession, tenant_id: str) -> Dict:
        """Retorna o uso atual do tenant comparado com os limites do plano."""
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant não encontrado.")

        plan = settings.PLANS.get(tenant.plan, settings.PLANS["free"])

        # Contar documentos
        result = await db.execute(
            select(func.count(Document.id)).where(Document.tenant_id == tenant_id)
        )
        doc_count = result.scalar() or 0

        # Calcular storage usado
        result = await db.execute(
            select(func.sum(Document.file_size)).where(Document.tenant_id == tenant_id)
        )
        storage_bytes = result.scalar() or 0

        return {
            "plan": {
                "name": plan["name"],
                "slug": tenant.plan,
            },
            "queries": {
                "used": tenant.queries_this_month,
                "limit": plan["max_queries_per_month"],
                "remaining": max(0, plan["max_queries_per_month"] - tenant.queries_this_month)
                    if plan["max_queries_per_month"] > 0 else -1,
            },
            "documents": {
                "used": doc_count,
                "limit": plan["max_documents"],
                "remaining": max(0, plan["max_documents"] - doc_count)
                    if plan["max_documents"] > 0 else -1,
            },
            "storage": {
                "used_bytes": storage_bytes,
                "used_mb": round(storage_bytes / 1024 / 1024, 2),
                "max_file_size_mb": plan["max_file_size_mb"],
            },
            "limits": {
                "max_users": plan["max_users"],
                "models": plan["models"],
            },
            "reset_at": tenant.queries_reset_at.isoformat() if tenant.queries_reset_at else None,
        }

    async def check_query_limit(self, db: AsyncSession, tenant_id: str) -> bool:
        """Verifica se o tenant ainda pode fazer queries."""
        tenant = await db.get(Tenant, tenant_id)
        plan = settings.PLANS.get(tenant.plan, settings.PLANS["free"])
        max_q = plan["max_queries_per_month"]
        if max_q < 0:
            return True  # ilimitado
        return tenant.queries_this_month < max_q

    async def increment_query_count(self, db: AsyncSession, tenant_id: str) -> None:
        """Incrementa o contador de queries do tenant."""
        tenant = await db.get(Tenant, tenant_id)
        tenant.queries_this_month += 1

    async def reset_monthly_counters(self, db: AsyncSession) -> int:
        """Reseta contadores mensais de todos os tenants. Executar via cron/scheduler."""
        result = await db.execute(select(Tenant))
        tenants = result.scalars().all()
        count = 0
        for tenant in tenants:
            tenant.queries_this_month = 0
            tenant.queries_reset_at = datetime.now(timezone.utc)
            count += 1
        return count
