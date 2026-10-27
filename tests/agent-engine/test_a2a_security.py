"""Real ASGI authorization boundary test; official SDK conformance is separate."""
import httpx
import pytest
from agent_runtime.official_a2a import (
    A2AIdentity,
    AuthenticatedA2AASGI,
    current_a2a_identity,
)
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from agent_runtime import A2ABoundary
from test_engine import build, manifest, Registry, task


def make_app(*, released=True):
    spec = build(task('read', ['read'], ['read'], []),
                 Registry([manifest('read', ['read'], ['read'], [])]))
    async def handler(request):
        identity = current_a2a_identity()
        return PlainTextResponse(f'{identity.tenant_id}:{identity.principal}')
    boundary = A2ABoundary(released_spec_digests=frozenset({spec.artifact_digest})
                           if released else frozenset(),
                           authorize=lambda principal, tenant: principal == 'trusted' and tenant == 'buyer')
    def authenticate(token):
        return {'good': A2AIdentity('buyer', 'trusted'),
                'wrong-tenant': A2AIdentity('seller', 'trusted')}.get(token)
    return AuthenticatedA2AASGI(Starlette(routes=[Route('/', handler)]),
                                 spec=spec, boundary=boundary, authenticate=authenticate)

@pytest.mark.asyncio
async def test_a2a_denies_spoofed_tenant_and_anonymous():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app()),
                                 base_url='http://example.test') as client:
        assert (await client.get('/')).status_code == 401
        assert (await client.get('/', headers={'Authorization': 'Bearer forged',
                 'x-tenant-id': 'buyer'})).status_code == 401
        assert (await client.get('/', headers={'Authorization': 'Bearer wrong-tenant',
                 'x-tenant-id': 'buyer'})).status_code == 403
        good = await client.get('/', headers={'Authorization': 'Bearer good',
                                              'x-tenant-id': 'evil'})
        assert good.status_code == 200 and good.text == 'buyer:trusted'

@pytest.mark.asyncio
async def test_a2a_revoked_spec_denies_valid_token():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app(released=False)),
                                 base_url='http://example.test') as client:
        assert (await client.get('/', headers={'Authorization': 'Bearer good'})).status_code == 403

def test_sdk_factory_rejects_unreleased_spec_before_import():
    from agent_runtime.official_a2a import create_official_a2a_app
    from agent_runtime import RuntimeDenied
    spec = build(task('read', ['read'], ['read'], []),
                 Registry([manifest('read', ['read'], ['read'], [])]))
    with pytest.raises(RuntimeDenied, match='A2A_NOT_RELEASED'):
        create_official_a2a_app(spec=spec, runtime=None,
            boundary=A2ABoundary(released_spec_digests=frozenset(), authorize=lambda *_: True),
            agent_card=None, authenticate=lambda _: None)

@pytest.mark.asyncio
async def test_a2a_lifespan_delegates_without_authentication():
    spec = build(task('read', ['read'], ['read'], []),
                 Registry([manifest('read', ['read'], ['read'], [])]))
    received = []
    async def inner(scope, receive, send):
        received.append(scope['type'])
    app = AuthenticatedA2AASGI(inner, spec=spec,
        boundary=A2ABoundary(released_spec_digests=frozenset({spec.artifact_digest}),
                             authorize=lambda *_: True), authenticate=lambda _: None)
    await app({'type': 'lifespan'}, None, None)
    assert received == ['lifespan']

@pytest.mark.asyncio
async def test_external_release_revocation_takes_effect_without_restart():
    spec = build(task('read', ['read'], ['read'], []),
                 Registry([manifest('read', ['read'], ['read'], [])]))
    releases = {('buyer',spec.artifact_digest): True}
    boundary = A2ABoundary(released_spec_digests=frozenset({spec.artifact_digest}),
        authorize=lambda principal,tenant: principal=='trusted' and tenant=='buyer',
        release_lookup=lambda tenant,digest: releases.get((tenant,digest),False))
    async def handler(request):
        return PlainTextResponse('available')
    app = AuthenticatedA2AASGI(Starlette(routes=[Route('/',handler)]),spec=spec,
        boundary=boundary,authenticate=lambda token: A2AIdentity('buyer','trusted')
        if token=='good' else None)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url='http://localhost') as client:
        assert (await client.get('/',headers={'Authorization':'Bearer good'})).status_code==200
        releases[('buyer',spec.artifact_digest)]=False
        assert (await client.get('/',headers={'Authorization':'Bearer good'})).status_code==403

@pytest.mark.asyncio
async def test_a2a_invalid_identity_resolver_response_fails_closed():
    app = make_app()
    app.authenticate = lambda token: {'tenant_id': 'buyer', 'principal': 'trusted'}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url='http://example.test') as client:
        response = await client.get('/', headers={'Authorization': 'Bearer good'})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_a2a_release_service_failure_fails_closed():
    app = make_app()
    app.boundary.authorize_request = lambda **kwargs: (_ for _ in ()).throw(
        RuntimeError('private internal error'))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url='http://example.test') as client:
        response = await client.get('/', headers={'Authorization': 'Bearer good'})
    assert response.status_code == 403
    assert 'private' not in response.text


@pytest.mark.asyncio
async def test_a2a_rejects_duplicate_authorization_headers():
    app = make_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url='http://example.test') as client:
        response = await client.get('/', headers=[('Authorization', 'Bearer good'),
                                                   ('Authorization', 'Bearer good')])
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_a2a_denies_tampered_spec_even_if_digest_was_released():
    app = make_app()
    app.spec = app.spec.model_copy(update={'system_prompt': 'injected prompt'})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url='http://example.test') as client:
        response = await client.get('/', headers={'Authorization': 'Bearer good'})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_a2a_single_principal_scope_blocks_authorized_other_principal():
    # Even if two principals have general tenant access, the same task store
    # must never be shared across them in this isolated candidate SDK adapter.
    app = make_app()
    app.principal_scope = 'trusted'
    app.authenticate = lambda token: (
        A2AIdentity('buyer', 'trusted') if token == 'trusted'
        else A2AIdentity('buyer', 'viewer') if token == 'viewer' else None)
    app.boundary.authorize = lambda principal, tenant: tenant == 'buyer' and principal in {'trusted','viewer'}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url='http://example.test') as client:
        assert (await client.get('/', headers={'Authorization': 'Bearer trusted'})).status_code == 200
        assert (await client.get('/', headers={'Authorization': 'Bearer viewer'})).status_code == 403


def test_official_a2a_factory_requires_principal_scope_even_before_sdk_import():
    from agent_runtime.official_a2a import create_official_a2a_app
    from agent_runtime import Decision, Runtime, RuntimeDenied, ToolPolicy, VerifiedToolGateway, EffectLedger
    from test_engine import ScriptedModel, FakeTools
    spec = build(task('read', ['read'], ['read'], []),
                 Registry([manifest('read', ['read'], ['read'], [])]))
    b = spec.selected_tools[0]
    gateway = VerifiedToolGateway(FakeTools(), EffectLedger(), policies={'read':ToolPolicy(
        tenant_id='buyer',tool_id='read',version=b.version,manifest_digest=b.digest,
        scopes=frozenset(b.granted_scopes),effect_mode='read',input_schema={'type':'object'},
        output_schema={'type':'object'})})
    runtime = Runtime(ScriptedModel([Decision(kind='final', text='ok')]), gateway,
                      approved_spec_digests=frozenset({spec.artifact_digest}))
    boundary = A2ABoundary(released_spec_digests=frozenset({spec.artifact_digest}),
                           authorize=lambda principal, tenant: True)
    with pytest.raises(RuntimeDenied, match='A2A_PRINCIPAL_SCOPE_REQUIRED'):
        create_official_a2a_app(spec=spec, runtime=runtime, boundary=boundary,
                                agent_card=None, authenticate=lambda token: None)
