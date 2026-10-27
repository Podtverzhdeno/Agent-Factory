"""A2A security boundary only; do not invent an ad-hoc A2A wire protocol."""
from __future__ import annotations
from .core import RuntimeDenied

class A2ABoundary:
    def __init__(self, *, released_spec_digests: frozenset[str], authorize):
        self.released_spec_digests = released_spec_digests
        self.authorize = authorize

    def authorize_request(self, *, tenant_id: str, principal: str, spec) -> None:
        if not self.authorize(principal, tenant_id):
            raise RuntimeDenied('A2A_UNAUTHORIZED')
        if spec.tenant_id != tenant_id:
            raise RuntimeDenied('A2A_TENANT_DENIED')
        if spec.artifact_digest not in self.released_spec_digests:
            raise RuntimeDenied('A2A_NOT_RELEASED')

    def official_sdk_available(self) -> bool:
        try:
            import a2a.server
            return True
        except ImportError:
            return False
