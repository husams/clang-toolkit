// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_edge.proto

import type { Long } from '@grpc/proto-loader';

export interface CfgEdge {
  'reachableBlock'?: (number | string | Long);
  'possiblyUnreachableBlock'?: (number | string | Long);
  'isReachable'?: (boolean);
  '_reachableBlock'?: "reachableBlock";
  '_possiblyUnreachableBlock'?: "possiblyUnreachableBlock";
}

export interface CfgEdge__Output {
  'reachableBlock'?: (string);
  'possiblyUnreachableBlock'?: (string);
  'isReachable': (boolean);
  '_reachableBlock'?: "reachableBlock";
  '_possiblyUnreachableBlock'?: "possiblyUnreachableBlock";
}
