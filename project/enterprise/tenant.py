from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass

from config.settings import settings

active_tenant = ContextVar("active_tenant", default=None)


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str | None = None
    department_id: str | None = None
    project_id: str | None = None

    def namespace(self, base: str) -> str:
        if not settings.TENANCY_ENABLED:
            return base
        values = {"base": base, "tenant": self.tenant_id or settings.DEFAULT_TENANT_ID,
                  "department": self.department_id or "default", "project": self.project_id or "default"}
        return settings.TENANT_NAMESPACE_TEMPLATE.format(**values)

    def metadata_filter(self) -> dict:
        if not settings.TENANCY_ENABLED:
            return {}
        return {key: value for key, value in {
            "tenant_id": self.tenant_id, "department_id": self.department_id,
            "project_id": self.project_id,
        }.items() if value}


def current_tenant() -> TenantContext:
    return active_tenant.get() or TenantContext(tenant_id=settings.DEFAULT_TENANT_ID or None)
