"""Proposed internal HTTP adapter; identity must be supplied by trusted middleware.

Never accepts caller-supplied ObservedRun values. Worker calls workflow.process()
through its authenticated internal channel.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from .application import EvaluationWorkflow
from .core import AccessDenied, EvaluationRequest, InvalidEvidence, Principal


class EvaluationRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(min_length=1)
    agent_spec_ref: str = Field(min_length=1)
    agent_spec_digest: str = Field(min_length=1)
    dataset_version_ref: str = Field(min_length=1)
    policy_ref: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    evaluation_run_id: str = Field(min_length=1)
    baseline_spec_ref: str | None = None


class EvaluationJobBody(BaseModel):
    tenant_id: str
    evaluation_run_id: str
    status: str
    error_code: str | None = None
    result: dict | None = None


def create_app(workflow: EvaluationWorkflow, authenticate: Callable[[], Principal]) -> FastAPI:
    """Authentication is a required dependency; never trust X-Tenant headers."""
    app = FastAPI(title="Agent Factory Evaluation (proposed)", version="0.1.0")

    @app.post("/internal/evaluations", response_model=EvaluationJobBody,
              status_code=status.HTTP_202_ACCEPTED)
    def submit(body: EvaluationRequestBody, principal: Principal = Depends(authenticate)):
        try:
            job = workflow.submit(principal, EvaluationRequest(**body.model_dump()))
        except AccessDenied:
            raise HTTPException(status_code=403, detail="forbidden") from None
        except InvalidEvidence:
            raise HTTPException(status_code=409, detail="invalid or conflicting evaluation request") from None
        return EvaluationJobBody(tenant_id=job.tenant_id,
                                 evaluation_run_id=job.evaluation_run_id, status=job.status)

    @app.get("/internal/evaluations/{run_id}", response_model=EvaluationJobBody)
    def get(run_id: str, principal: Principal = Depends(authenticate)):
        try:
            job = workflow.get(principal, run_id)
        except (AccessDenied, KeyError):
            raise HTTPException(status_code=404, detail="evaluation run not found") from None
        return EvaluationJobBody(tenant_id=job.tenant_id,
                                 evaluation_run_id=job.evaluation_run_id,
                                 status=job.status, error_code=job.error_code,
                                 result=asdict(job.result) if job.result else None)

    return app
