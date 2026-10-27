"""Production PostgreSQL checkpoint adapter must refuse permissive deserialization."""
import pytest
from agent_runtime.langgraph_adapter import postgres_checkpointer

from agent_runtime import RuntimeDenied


def test_pg_checkpointer_requires_strict_deserialization(monkeypatch):
    monkeypatch.delenv('LANGGRAPH_STRICT_MSGPACK', raising=False)
    with pytest.raises(RuntimeDenied, match='UNSAFE_CHECKPOINT_DESERIALIZATION'):
        postgres_checkpointer('postgresql://example.invalid/unused')
    monkeypatch.setenv('LANGGRAPH_STRICT_MSGPACK', 'false')
    with pytest.raises(RuntimeDenied, match='UNSAFE_CHECKPOINT_DESERIALIZATION'):
        postgres_checkpointer('postgresql://example.invalid/unused')
