// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/traverse_stream.proto

import type { Long } from '@grpc/proto-loader';

export interface TraverseCompleted {
  'nodeCount'?: (number | string | Long);
  'depthLimited'?: (boolean);
}

export interface TraverseCompleted__Output {
  'nodeCount': (string);
  'depthLimited': (boolean);
}
