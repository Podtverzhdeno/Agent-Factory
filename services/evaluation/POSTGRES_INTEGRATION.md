# Real PostgreSQL integration test — isolated and opt-in

Current status: the repository has executable SQLAlchemy persistence and recovery tests, but PostgreSQL has NOT been started in the current execution environment. Local tests run against SQLite; the real PostgreSQL test is SKIPPED unless configured explicitly.

To run against an isolated PostgreSQL test instance with Docker Compose:

```bash
docker compose -f services/evaluation/compose.postgres-test.yml up -d --wait
export AGENT_FACTORY_TEST_POSTGRES_DSN="postgresql+psycopg://evaluation_test:evaluation_local_test_only@127.0.0.1:55432/agent_factory_quality_test"
export AF_QUALITY_ALLOW_POSTGRES_IT=YES
python -m pip install "psycopg[binary]>=3.2" "sqlalchemy>=2.0" pytest
pytest -q tests/quality-engine/test_postgres_integration.py -rs
docker compose -f services/evaluation/compose.postgres-test.yml down -v
```

The test requires an explicitly named *_test database, creates a random isolated schema, cleans it up and verifies persisted gold, SQL job leasing and restart behavior. Never use a production DSN or an existing business database. SQLite tests already verify outbox atomicity and concurrent worker fencing; a live PostgreSQL/Kafka/Runtime E2E requires separate integration evidence.

This compose file is a development test fixture, not an ADR-0002 topology or a production deployment.
