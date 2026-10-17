// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_stream.proto

import type { Long } from '@grpc/proto-loader';

export interface CfgGraphCompleted {
  'graphIndex'?: (number | string | Long);
  'blockCount'?: (number | string | Long);
  'elementCount'?: (number | string | Long);
  'isComplete'?: (boolean);
}

export interface CfgGraphCompleted__Output {
  'graphIndex': (string);
  'blockCount': (string);
  'elementCount': (string);
  'isComplete': (boolean);
}
