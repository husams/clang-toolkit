// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { APStructBaseValue as _ctk_ast_v1_APStructBaseValue, APStructBaseValue__Output as _ctk_ast_v1_APStructBaseValue__Output } from '../../../ctk/ast/v1/APStructBaseValue.js';
import type { APStructFieldValue as _ctk_ast_v1_APStructFieldValue, APStructFieldValue__Output as _ctk_ast_v1_APStructFieldValue__Output } from '../../../ctk/ast/v1/APStructFieldValue.js';

export interface APStructValue {
  'baseValues'?: (_ctk_ast_v1_APStructBaseValue)[];
  'fieldValues'?: (_ctk_ast_v1_APStructFieldValue)[];
}

export interface APStructValue__Output {
  'baseValues': (_ctk_ast_v1_APStructBaseValue__Output)[];
  'fieldValues': (_ctk_ast_v1_APStructFieldValue__Output)[];
}
