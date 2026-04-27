"""
Serviço de billing (planos e pagamentos).
Integra com Stripe quando configurado, ou opera em modo local.
"""

from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.models import Tenant

settings = get_settings()


class BillingService:
    """Gestão de planos e billing."""

    def __init__(self):
        self.stripe = None
        if settings.STRIPE_SECRET_KEY:
            try:
                import stripe
                stripe.api_key = settings.STRIPE_SECRET_KEY
                self.stripe = stripe
            except ImportError:
                pass  # Stripe não instalado — modo local

    def get_plans(self) -> list:
        """Retorna todos os planos disponíveis."""
        return [
            {
                "slug": slug,
                "name": config["name"],
                "price_monthly": config["price_monthly"],
                "max_documents": config["max_documents"],
                "max_queries_per_month": config["max_queries_per_month"],
                "max_file_size_mb": config["max_file_size_mb"],
                "max_users": config["max_users"],
                "models": config["models"],
            }
            for slug, config in settings.PLANS.items()
        ]

    async def get_current_plan(self, db: AsyncSession, tenant_id: str) -> Dict:
        """Retorna o plano atual do tenant."""
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant não encontrado.")

        plan_config = settings.PLANS.get(tenant.plan, settings.PLANS["free"])
        return {
            "slug": tenant.plan,
            **plan_config,
        }

    async def upgrade_plan(
        self,
        db: AsyncSession,
        tenant_id: str,
        new_plan: str,
    ) -> Dict:
        """
        Atualiza o plano do tenant.
        Em produção, isso seria feito via webhook do Stripe após pagamento.
        """
        if new_plan not in settings.PLANS:
            raise ValueError(f"Plano '{new_plan}' não existe.")

        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant não encontrado.")

        old_plan = tenant.plan
        tenant.plan = new_plan

        return {
            "tenant_id": tenant_id,
            "old_plan": old_plan,
            "new_plan": new_plan,
            "message": f"Plano atualizado de {old_plan} para {new_plan}.",
        }

    async def create_checkout_session(
        self,
        tenant_id: str,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> Optional[str]:
        """
        Cria uma sessão de checkout no Stripe.
        Retorna a URL do checkout ou None se Stripe não estiver configurado.
        """
        if not self.stripe:
            return None

        # Mapeamento de planos para Stripe Price IDs
        # Em produção, configurar via .env
        price_ids = {
            "pro": "price_pro_monthly_id",
            "enterprise": "price_enterprise_monthly_id",
        }

        price_id = price_ids.get(plan)
        if not price_id:
            raise ValueError(f"Plano '{plan}' não tem integração com Stripe.")

        session = self.stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"tenant_id": tenant_id, "plan": plan},
        )

        return session.url

    async def handle_webhook(self, payload: bytes, signature: str) -> Dict:
        """
        Processa webhooks do Stripe (pagamento confirmado, cancelamento, etc).
        """
        if not self.stripe:
            raise ValueError("Stripe não configurado.")

        event = self.stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            tenant_id = session["metadata"]["tenant_id"]
            plan = session["metadata"]["plan"]
            return {"action": "upgrade", "tenant_id": tenant_id, "plan": plan}

        elif event["type"] == "customer.subscription.deleted":
            session = event["data"]["object"]
            tenant_id = session.get("metadata", {}).get("tenant_id")
            return {"action": "downgrade", "tenant_id": tenant_id, "plan": "free"}

        return {"action": "ignored", "type": event["type"]}
