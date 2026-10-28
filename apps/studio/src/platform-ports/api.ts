import type { SourceStamp } from "@studio/contracts";
/** Type-only safe transport boundary; A01 must implement real authenticated BFF. */
export interface StudioClient { getCapabilities(): Promise<{stamp: SourceStamp; features: readonly unknown[]}>; }
export class SourceUnavailableError extends Error { constructor() { super("C0_PREP_NOT_CONNECTED"); this.name="SourceUnavailableError"; } }
export const unavailableStudioClient: StudioClient = { getCapabilities: async () => { throw new SourceUnavailableError(); } };
