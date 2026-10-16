// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_stream.proto

import type { Long } from '@grpc/proto-loader';

export interface CallGraphCompleted {
  'graphCount'?: (number | string | Long);
  'nodeCount'?: (number | string | Long);
  'edgeCount'?: (number | string | Long);
  'callSiteCount'?: (number | string | Long);
  'isComplete'?: (boolean);
}

export interface CallGraphCompleted__Output {
  'graphCount': (string);
  'nodeCount': (string);
  'edgeCount': (string);
  'callSiteCount': (string);
  'isComplete': (boolean);
}
