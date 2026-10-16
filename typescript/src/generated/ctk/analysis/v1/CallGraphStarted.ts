// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_stream.proto

import type { CallGraphResponse as _ctk_analysis_v1_CallGraphResponse, CallGraphResponse__Output as _ctk_analysis_v1_CallGraphResponse__Output } from '../../../ctk/analysis/v1/CallGraphResponse.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphStarted {
  'graphIndex'?: (number | string | Long);
  'snapshotGeneration'?: (number | string | Long);
  'graph'?: (_ctk_analysis_v1_CallGraphResponse | null);
}

export interface CallGraphStarted__Output {
  'graphIndex': (string);
  'snapshotGeneration': (string);
  'graph': (_ctk_analysis_v1_CallGraphResponse__Output | null);
}
