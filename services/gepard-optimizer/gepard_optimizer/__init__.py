"""Sandbox-only GEPARD optimizer adapter (no production mutation)."""
from .core import CandidatePatch, OptimizationRequest, OptimizerAdapter, OptimizerInputError
from .dspy_backend import DspyGepaBackend, GepaExecution, GepaUnavailableError
