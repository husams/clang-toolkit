// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/common.proto

import type { FieldState as _ctk_ast_v1_FieldState, FieldState__Output as _ctk_ast_v1_FieldState__Output } from '../../../ctk/ast/v1/FieldState.js';

export interface FieldAvailability {
  'fieldPath'?: (string);
  'state'?: (_ctk_ast_v1_FieldState);
  'reason'?: (string);
  '_fieldPath'?: "fieldPath";
  '_state'?: "state";
  '_reason'?: "reason";
}

export interface FieldAvailability__Output {
  'fieldPath'?: (string);
  'state'?: (_ctk_ast_v1_FieldState__Output);
  'reason'?: (string);
  '_fieldPath'?: "fieldPath";
  '_state'?: "state";
  '_reason'?: "reason";
}
