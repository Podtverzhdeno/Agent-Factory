# GEPARD Optimizer Adapter — workstream 05

Typed, immutable candidate proposal only. Source: `gepard_optimizer/core.py`.
The default backend is **deterministic mock, not DSPy GEPA**. An injected callable is an integration seam for a real optimizer; it is not a claim of completed GEPA research or quality improvement.

Requires authorized tenant, pinned source spec, separately referenced tuning/validation datasets, bounded candidate budget and allowed surfaces. Rejects holdout references based on type/name checks; full role enforcement lives in evaluator-owned vault and service IAM. Never grants tools/MCP permissions or modifies released agents.

Returned patch has SHA256 digest and status REQUIRES_INDEPENDENT_EVALUATION. Promotion is exclusively workstream 01's owner-authorized release gate after real independent evaluation.

Remaining: actual DSPy/GEPA integration, secure cross-service auth, typed prompt/artifact repository and trace-feedback callback, budgeted optimization jobs, negative tests against live Runtime in sandbox.
