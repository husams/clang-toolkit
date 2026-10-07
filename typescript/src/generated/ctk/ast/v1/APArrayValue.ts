// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { APValue as _ctk_ast_v1_APValue, APValue__Output as _ctk_ast_v1_APValue__Output } from '../../../ctk/ast/v1/APValue.js';
import type { Long } from '@grpc/proto-loader';

export interface APArrayValue {
  'initializedElements'?: (_ctk_ast_v1_APValue)[];
  'filler'?: (_ctk_ast_v1_APValue | null);
  'size'?: (number | string | Long);
  '_size'?: "size";
}

export interface APArrayValue__Output {
  'initializedElements': (_ctk_ast_v1_APValue__Output)[];
  'filler': (_ctk_ast_v1_APValue__Output | null);
  'size'?: (string);
  '_size'?: "size";
}
