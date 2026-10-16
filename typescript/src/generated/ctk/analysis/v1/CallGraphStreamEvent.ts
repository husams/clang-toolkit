// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_stream.proto

import type { CallGraphStarted as _ctk_analysis_v1_CallGraphStarted, CallGraphStarted__Output as _ctk_analysis_v1_CallGraphStarted__Output } from '../../../ctk/analysis/v1/CallGraphStarted.js';
import type { CallGraphNodeEvent as _ctk_analysis_v1_CallGraphNodeEvent, CallGraphNodeEvent__Output as _ctk_analysis_v1_CallGraphNodeEvent__Output } from '../../../ctk/analysis/v1/CallGraphNodeEvent.js';
import type { CallGraphEdgeEvent as _ctk_analysis_v1_CallGraphEdgeEvent, CallGraphEdgeEvent__Output as _ctk_analysis_v1_CallGraphEdgeEvent__Output } from '../../../ctk/analysis/v1/CallGraphEdgeEvent.js';
import type { CallGraphCallSiteEvent as _ctk_analysis_v1_CallGraphCallSiteEvent, CallGraphCallSiteEvent__Output as _ctk_analysis_v1_CallGraphCallSiteEvent__Output } from '../../../ctk/analysis/v1/CallGraphCallSiteEvent.js';
import type { CallGraphCompleted as _ctk_analysis_v1_CallGraphCompleted, CallGraphCompleted__Output as _ctk_analysis_v1_CallGraphCompleted__Output } from '../../../ctk/analysis/v1/CallGraphCompleted.js';

export interface CallGraphStreamEvent {
  'graphStarted'?: (_ctk_analysis_v1_CallGraphStarted | null);
  'node'?: (_ctk_analysis_v1_CallGraphNodeEvent | null);
  'edge'?: (_ctk_analysis_v1_CallGraphEdgeEvent | null);
  'callSite'?: (_ctk_analysis_v1_CallGraphCallSiteEvent | null);
  'completed'?: (_ctk_analysis_v1_CallGraphCompleted | null);
  'event'?: "graphStarted"|"node"|"edge"|"callSite"|"completed";
}

export interface CallGraphStreamEvent__Output {
  'graphStarted'?: (_ctk_analysis_v1_CallGraphStarted__Output | null);
  'node'?: (_ctk_analysis_v1_CallGraphNodeEvent__Output | null);
  'edge'?: (_ctk_analysis_v1_CallGraphEdgeEvent__Output | null);
  'callSite'?: (_ctk_analysis_v1_CallGraphCallSiteEvent__Output | null);
  'completed'?: (_ctk_analysis_v1_CallGraphCompleted__Output | null);
  'event'?: "graphStarted"|"node"|"edge"|"callSite"|"completed";
}
