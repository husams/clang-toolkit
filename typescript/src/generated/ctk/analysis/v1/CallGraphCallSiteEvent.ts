// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_stream.proto

import type { CallGraphCallSite as _ctk_analysis_v1_CallGraphCallSite, CallGraphCallSite__Output as _ctk_analysis_v1_CallGraphCallSite__Output } from '../../../ctk/analysis/v1/CallGraphCallSite.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphCallSiteEvent {
  'graphIndex'?: (number | string | Long);
  'callSite'?: (_ctk_analysis_v1_CallGraphCallSite | null);
}

export interface CallGraphCallSiteEvent__Output {
  'graphIndex': (string);
  'callSite': (_ctk_analysis_v1_CallGraphCallSite__Output | null);
}
