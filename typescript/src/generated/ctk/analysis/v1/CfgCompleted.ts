// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_stream.proto

import type { Long } from '@grpc/proto-loader';

export interface CfgCompleted {
  'graphCount'?: (number | string | Long);
  'blockCount'?: (number | string | Long);
  'elementCount'?: (number | string | Long);
}

export interface CfgCompleted__Output {
  'graphCount': (string);
  'blockCount': (string);
  'elementCount': (string);
}
