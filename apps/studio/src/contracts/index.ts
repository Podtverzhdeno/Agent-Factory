/** Proposed C0 view models, NOT confirmed deployed backend APIs. */
export type SourceState = "COMPLETE"|"PARTIAL"|"UNAVAILABLE"|"STALE"|"UNSUPPORTED";
export type EffectiveFeature = "ROADMAP_IDEA"|"PLANNED"|"DISABLED"|"PREVIEW"|"AVAILABLE"|"DEGRADED"|"FORBIDDEN";
export interface SourceStamp { source: string; sourceAsOf: string|null; completeness: SourceState; revision: string|null; }
export interface Page<T> { items: readonly T[]; nextCursor: string|null; stamp: SourceStamp; }
export interface SafeError { code: string; messageKey: string; retryable: boolean; requiredAction?: string; requestRef?: string; source?: string; }
export interface FeatureAvailability { featureId: string; availability: EffectiveFeature; allowedActions: readonly string[]; stamp: SourceStamp; }
export const UNAVAILABLE_STAMP: SourceStamp = { source: "C0_PREP_NOT_CONNECTED", sourceAsOf: null, completeness: "UNAVAILABLE", revision: null };
