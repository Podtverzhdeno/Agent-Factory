/** Proposed, source-safe UI/BFF read models. Never map untrusted JSON without validation. */
import type { SourceStamp } from "./index";
export interface ActionDescriptor {
  id: string;
  allowed: boolean;
  reasonCode?: string;
  requiresConfirmation: boolean;
  requiresApproval: boolean;
}
export interface TaskView {
  taskId: string; revision: string; status: string;
  objective: string; ownerRef: string; missingRequirements: readonly string[];
  artifactCount: number | null; snapshotRef: string | null;
  allowedActions: readonly ActionDescriptor[]; stamp: SourceStamp;
}
export interface AgentSummary {
  agentId: string; displayName: string; businessOutcome: string; ownerRef: string;
  environment: "SANDBOX" | "PRODUCTION";
  candidateSpecDigest: string | null; releasedSpecDigest: string | null;
  quality: "PASSED" | "FAILED" | "BLOCKED" | "INCONCLUSIVE" |
    "UNAVAILABLE" | "UNKNOWN_UNSUPPORTED_VERSION";
  latestRunAt: string | null; actionRequired: string | null; stamp: SourceStamp;
}
export interface WorkflowView {
  workflowId: string; taskSnapshotRef: string; agentId: string | null;
  backendState: string; displayStage: string; revision: number;
  pendingOperationId: string | null; requiredAction: string | null;
  spent: {amount: string; currency: string} | null; stamp: SourceStamp;
}
export interface RunView {
  runId: string; agentId: string; specDigest: string;
  environment: "SANDBOX" | "PRODUCTION"; status: string;
  outputArtifactRefs: readonly string[];
  effectVerification: "NOT_REQUIRED" | "UNCONFIRMED" |
    "CONFIRMED_BY_EXTERNAL_RECEIPT" | "RECONCILIATION_REQUIRED" | "UNAVAILABLE";
  traceRef: string | null;
  usage: {amount:string;currency:string} | null;
  stamp: SourceStamp;
}
export interface EvaluationView {
  evaluationRunId: string; specDigest: string; datasetRevision: string;
  status: "PASSED"|"FAILED"|"BLOCKED"|"INCONCLUSIVE"|"UNAVAILABLE";
  independentVerified: boolean; evidenceRef: string | null;
  requiredEffectsVerified: boolean | null;
  cases: {passed: number | null;total:number|null}; stamp: SourceStamp;
}
