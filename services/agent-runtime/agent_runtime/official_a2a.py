"""Isolated official A2A SDK v1 adapter; no socket or release side effects."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Protocol

from agent_builder import AgentSpec

from .a2a_adapter import A2ABoundary
from .core import Runtime, RuntimeDenied


@dataclass(frozen=True)
class A2AIdentity:
    tenant_id: str
    principal: str

class BearerAuthenticator(Protocol):
    def __call__(self, token: str) -> A2AIdentity | None: ...

_active_identity: ContextVar[A2AIdentity | None] = ContextVar('a2a_identity', default=None)

def current_a2a_identity() -> A2AIdentity:
    identity = _active_identity.get()
    if identity is None:
        raise RuntimeDenied('A2A_UNAUTHENTICATED_CONTEXT')
    return identity

class AuthenticatedA2AASGI:
    """Enforce bearer identity on every SDK route, including Agent Card.

    Only the trusted token resolver supplies tenant/principal. Never accept
    tenant data from untrusted headers or JSON-RPC payloads.
    """
    def __init__(self, app, *, spec: AgentSpec, boundary: A2ABoundary,
                 authenticate: BearerAuthenticator,
                 principal_scope: str | None = None):
        self.app, self.spec, self.boundary = app, spec, boundary
        self.authenticate = authenticate
        self.principal_scope = principal_scope

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            await self.app(scope, receive, send)
            return
        if scope['type'] != 'http':
            raise RuntimeDenied('A2A_HTTP_ONLY')
        authorization = [value for key, value in scope.get('headers', [])
                         if key.lower() == b'authorization']
        if (len(authorization) != 1 or len(authorization[0]) > 4103
                or not authorization[0].startswith(b'Bearer ')):
            await self._deny(send, 401)
            return
        try:
            token = authorization[0][7:].decode('ascii')
            identity = self.authenticate(token) if token else None
        except Exception:  # noqa: BLE001 - identity provider errors fail closed.
            identity = None
        if not isinstance(identity, A2AIdentity) or not identity.tenant_id or not identity.principal:
            await self._deny(send, 401)
            return
        if self.principal_scope is not None and identity.principal != self.principal_scope:
            # The candidate SDK uses a single shared in-memory TaskStore.
            # Prevent horizontal read access between authorized principals.
            await self._deny(send, 403)
            return
        try:
            self.boundary.authorize_request(tenant_id=identity.tenant_id,
                principal=identity.principal, spec=self.spec)
        except Exception:  # noqa: BLE001 - release authority errors fail closed.
            # Identity and release authorities are external dependencies. Fail closed.
            await self._deny(send, 403)
            return
        marker = _active_identity.set(identity)
        try:
            await self.app(scope, receive, send)
        finally:
            _active_identity.reset(marker)

    @staticmethod
    async def _deny(send, status: int) -> None:
        body = b'{"error":"access_denied"}'
        await send({'type': 'http.response.start', 'status': status,
                    'headers': [(b'content-type', b'application/json'),
                                (b'content-length', str(len(body)).encode())]})
        await send({'type': 'http.response.body', 'body': body})


def create_official_a2a_app(*, spec: AgentSpec, runtime: Runtime, boundary: A2ABoundary,
                            agent_card, authenticate: BearerAuthenticator,
                            principal_scope: str | None = None):
    """Create SDK routes only for a released/pinned AgentSpec in an isolated test.

    SDK conformance and production endpoint authentication require owner ADR.
    """
    if not spec.verify_digest() or not boundary.is_released(spec.tenant_id, spec.artifact_digest):
        raise RuntimeDenied('A2A_NOT_RELEASED')
    if spec.artifact_digest not in runtime.approved_spec_digests:
        raise RuntimeDenied('SPEC_NOT_PINNED')
    if not getattr(runtime.gateway, 'verified', False):
        raise RuntimeDenied('UNVERIFIED_TOOL_GATEWAY')
    if not principal_scope:
        raise RuntimeDenied('A2A_PRINCIPAL_SCOPE_REQUIRED')
    try:
        from a2a.server.agent_execution import AgentExecutor, RequestContext
        from a2a.server.events import EventQueue
        from a2a.server.request_handlers import DefaultRequestHandler
        from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
        from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
        from a2a.types import TaskState
        from a2a.helpers import get_message_text, new_task_from_user_message, new_text_message, new_text_part
        from starlette.applications import Starlette
    except ImportError as exc:
        raise RuntimeError('Official a2a-sdk v1 with Starlette is required') from exc

    class DelegatingExecutor(AgentExecutor):
        async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
            identity = current_a2a_identity()
            boundary.authorize_request(tenant_id=identity.tenant_id,
                principal=identity.principal, spec=spec)
            if context.message is None:
                raise RuntimeDenied('A2A_MESSAGE_REQUIRED')
            task = context.current_task
            if task is None:
                task = new_task_from_user_message(context.message)
                await event_queue.enqueue_event(task)
            updater = TaskUpdater(event_queue=event_queue,
                                  task_id=task.id, context_id=task.context_id)
            await updater.update_status(state=TaskState.TASK_STATE_WORKING,
                                        message=new_text_message('Processing'))
            request = get_message_text(context.message)
            result = await runtime.run(spec, tenant_id=identity.tenant_id,
                run_id=task.id, thread_id=task.context_id, request=request,
                trace_id='a2a:' + task.id)
            if result.status == 'COMPLETED':
                await updater.add_artifact(parts=[
                    new_text_part(text=result.answer, media_type='text/plain')])
                await updater.update_status(state=TaskState.TASK_STATE_COMPLETED,
                    message=new_text_message('Completed'))
            else:
                await updater.update_status(state=TaskState.TASK_STATE_FAILED,
                    message=new_text_message('Execution blocked'))

        async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
            from a2a.utils.errors import TaskNotCancelableError
            raise TaskNotCancelableError()

    handler = DefaultRequestHandler(agent_executor=DelegatingExecutor(),
                                    task_store=InMemoryTaskStore(), agent_card=agent_card)
    routes = [*create_agent_card_routes(agent_card), *create_jsonrpc_routes(handler, '/')]
    return AuthenticatedA2AASGI(Starlette(routes=routes), spec=spec,
                                 boundary=boundary, authenticate=authenticate,
                                 principal_scope=principal_scope)
