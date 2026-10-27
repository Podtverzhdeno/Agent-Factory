-- Isolated PostgreSQL proof-of-concept schema. Not activated without owner-approved ADR-0002.
-- No cross-service database reads. All primary/unique keys include tenant_id.
CREATE TABLE cp_workflow (
    tenant_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    payload TEXT NOT NULL,
    action_pending BOOLEAN NOT NULL,
    notification_pending BOOLEAN NOT NULL,
    terminal BOOLEAN NOT NULL,
    revision BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, workflow_id),
    UNIQUE (tenant_id, idempotency_key)
);
CREATE INDEX cp_workflow_pending_actions ON cp_workflow (tenant_id, workflow_id)
    WHERE action_pending AND NOT terminal;
CREATE INDEX cp_workflow_pending_events ON cp_workflow (tenant_id, workflow_id)
    WHERE notification_pending;

CREATE TABLE cp_agent_lock (
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, agent_id)
);
CREATE TABLE cp_agent_version (
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    version BIGINT NOT NULL CHECK (version >= 1),
    payload TEXT NOT NULL,
    PRIMARY KEY (tenant_id, agent_id, version),
    FOREIGN KEY (tenant_id, agent_id) REFERENCES cp_agent_lock (tenant_id, agent_id)
);
CREATE TABLE cp_agent_operation (
    tenant_id TEXT NOT NULL,
    operation_kind TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    result_json TEXT NOT NULL,
    PRIMARY KEY (tenant_id, operation_kind, idempotency_key)
);
CREATE TABLE cp_agent_transition (
    sequence_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    FOREIGN KEY (tenant_id, agent_id) REFERENCES cp_agent_lock (tenant_id, agent_id)
);
CREATE INDEX cp_agent_transition_history ON cp_agent_transition(tenant_id, agent_id, sequence_id);
