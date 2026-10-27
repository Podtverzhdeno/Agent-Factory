"""A2A security boundary only; do not invent an ad-hoc A2A wire protocol."""
from __future__ import annotations
from collections.abc import Callable
from .core import RuntimeDenied

class A2ABoundary:
    def __init__(self, *, released_spec_digests: frozenset[str], authorize,
                 release_lookup: Callable[[str, str], bool] | None = None):
        self.released_spec_digests = released_spec_digests
        self.authorize = authorize
        self._release_lookup = release_lookup

    def is_released(self, tenant_id: str, artifact_digest: str) -> bool:
        if self._release_lookup is None:
            return artifact_digest in self.released_spec_digests
        try:
            return bool(self._release_lookup(tenant_id, artifact_digest))
        except Exception:
            return False

    def authorize_request(self, *, tenant_id: str, principal: str, spec) -> None:
        if not spec.verify_digest():
            raise RuntimeDenied('A2A_SPEC_TAMPERED')
        if not self.authorize(principal, tenant_id):
            raise RuntimeDenied('A2A_UNAUTHORIZED')
        if spec.tenant_id != tenant_id:
            raise RuntimeDenied('A2A_TENANT_DENIED')
        if not self.is_released(tenant_id, spec.artifact_digest):
            raise RuntimeDenied('A2A_NOT_RELEASED')

    def official_sdk_available(self) -> bool:
        try:
            import a2a.server
            return True
        except ImportError:
            return False
