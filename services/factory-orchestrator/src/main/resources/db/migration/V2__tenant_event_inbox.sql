-- Forward-only migration; tenant-wide event deduplication. Requires V1.
-- A single event_id cannot acknowledge two workflows within the same tenant.
-- Inserted inside the same SQL transaction as workflow/outbox state.
CREATE TABLE cp_event_inbox (
    tenant_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL CHECK (char_length(fingerprint) = 64),
    PRIMARY KEY (tenant_id, event_id),
    FOREIGN KEY (tenant_id, workflow_id)
        REFERENCES cp_workflow (tenant_id, workflow_id)
);
CREATE INDEX cp_event_inbox_workflow ON cp_event_inbox (tenant_id, workflow_id);

