import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2] / "project"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from enterprise.reranking import DisabledReranker
from enterprise.tenant import TenantContext


def test_disabled_reranker_preserves_rank():
    first, second = object(), object()
    ranked = DisabledReranker().rerank("refund", [(first, .9), (second, .7)])
    assert [item.document for item in ranked] == [first, second]
    assert [item.rank for item in ranked] == [1, 2]


def test_tenant_namespace_is_backward_compatible(monkeypatch):
    from config.settings import settings
    monkeypatch.setattr(settings, "TENANCY_ENABLED", False)
    assert TenantContext(tenant_id="acme").namespace("document_child_chunks") == "document_child_chunks"
