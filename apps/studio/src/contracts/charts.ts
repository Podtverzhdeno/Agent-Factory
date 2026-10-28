/** C0 contract for exactly 15 logical chart templates; proposal-derived, not a live API. */
import type { SourceState } from "./index";
export const CHART_KINDS = [
  "trend", "stacked_bar", "horizontal_bar", "scatter", "heatmap",
  "funnel", "timeline", "waterfall", "sankey", "treemap",
  "distribution", "gauge", "dependency", "donut", "a2a_sequence",
] as const;
export type ChartKind = (typeof CHART_KINDS)[number];
export interface ChartWindow { from: string; to: string; timezone: string; granularity: string }
export interface ChartMeta {
  chartId: string;
  titleKey: string;
  kind: ChartKind;
  schemaVersion: string;
  sourceRefs: readonly string[];
  window: ChartWindow;
  unit: string;
  currency?: string | null;
  sampleCount: number | null;
  denominator?: number | null;
  sourceAsOf: string | null;
  revision: string | null;
  lastObservedAt: string | null;
  completeness: SourceState;
  redactionLevel: "PUBLIC" | "TENANT" | "OPERATOR_REDACTED";
}
export interface ChartTable {
  captionKey: string;
  columns: readonly {id: string; headingKey: string; unit?: string}[];
  rows: readonly Readonly<Record<string, string | number | null>>[];
  nextCursor: string | null;
}
interface Scalar { key: string; label: string; value: number | null }
interface Moment { at: string; value: number | null; count?: number | null }
interface Edge { from: string; to: string; value: number }
export type ChartPayload =
  | {kind:"trend"; variant:"line" | "area"; points: readonly Moment[]}
  | {kind:"stacked_bar"; categories: readonly string[]; series: readonly {key:string;values:readonly (number|null)[]}[]}
  | {kind:"horizontal_bar"; variant:"rank"|"error_interval"; points:readonly Scalar[]; intervals?:readonly (readonly [number,number])[]}
  | {kind:"scatter"; points: readonly {id:string;x:number;y:number;size?:number|null}[]}
  | {kind:"heatmap"; cells: readonly {xKey:string;yKey:string;value:number|null}[]}
  | {kind:"funnel"; stages: readonly {id:string;count:number;denominator:number|null}[]}
  | {kind:"timeline"; intervals: readonly {id:string;from:string;to:string;lane:string}[]}
  | {kind:"waterfall"; steps: readonly {id:string;delta:number;total?:number|null}[]}
  | {kind:"sankey"; nodes: readonly {id:string;label:string}[];edges:readonly Edge[]}
  | {kind:"treemap"; leaves: readonly {id:string;parentId:string|null;value:number}[]}
  | {kind:"distribution"; variant:"histogram"|"boxplot";bins: readonly {x:number;count:number}[];quartiles?:readonly number[]}
  | {kind:"gauge"; current:number;limit:number;unit:string}
  | {kind:"dependency"; nodes: readonly {id:string;label:string;state:string}[];edges:readonly {from:string;to:string}[]}
  | {kind:"donut"; slices: readonly Scalar[]}
  | {kind:"a2a_sequence"; events:readonly {eventRef:string;actorRef:string;recipientRef:string|null;occurredAt:string;eventType:string;disclosed:boolean}[]};
export type ChartResult =
  | {state:"loading"}
  | {state:"ready";meta:ChartMeta;payload:ChartPayload;table:ChartTable}
  | {state:"partial"|"stale";meta:ChartMeta;payload:ChartPayload;table:ChartTable;reasonCode:string}
  | {state:"empty";meta:ChartMeta;table:ChartTable}
  | {state:"unavailable"|"unsupported"|"forbidden"|"error";meta?:ChartMeta;reasonCode:string};
/** Chart adapter must verify meta.kind === payload.kind, source, dates and finite values at runtime. */
