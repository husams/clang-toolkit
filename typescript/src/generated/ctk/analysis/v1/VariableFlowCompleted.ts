// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/variable_flow.proto

import type { Long } from '@grpc/proto-loader';

export interface VariableFlowCompleted {
  'usageCount'?: (number | string | Long);
  'factCount'?: (number | string | Long);
  'findingCount'?: (number | string | Long);
  'blockCount'?: (number | string | Long);
  'iterations'?: (number | string | Long);
  'isComplete'?: (boolean);
}

export interface VariableFlowCompleted__Output {
  'usageCount': (string);
  'factCount': (string);
  'findingCount': (string);
  'blockCount': (string);
  'iterations': (string);
  'isComplete': (boolean);
}
