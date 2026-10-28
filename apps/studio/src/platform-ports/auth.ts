import type { FeatureAvailability } from "@studio/contracts";
/** Presentation only: owner services MUST re-check every action. */
export function canOfferAction(f:FeatureAvailability,actionId:string):boolean {return f.availability==="AVAILABLE"&&f.allowedActions.includes(actionId)}
