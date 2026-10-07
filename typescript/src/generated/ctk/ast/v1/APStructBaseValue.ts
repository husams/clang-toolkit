// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeDescription as _ctk_ast_v1_TypeDescription, TypeDescription__Output as _ctk_ast_v1_TypeDescription__Output } from '../../../ctk/ast/v1/TypeDescription.js';
import type { APValue as _ctk_ast_v1_APValue, APValue__Output as _ctk_ast_v1_APValue__Output } from '../../../ctk/ast/v1/APValue.js';

export interface APStructBaseValue {
  'type'?: (_ctk_ast_v1_TypeDescription | null);
  'value'?: (_ctk_ast_v1_APValue | null);
}

export interface APStructBaseValue__Output {
  'type': (_ctk_ast_v1_TypeDescription__Output | null);
  'value': (_ctk_ast_v1_APValue__Output | null);
}
