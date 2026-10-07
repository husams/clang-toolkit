// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';

export interface BitIntType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'bitWidth'?: (number);
  'isUnsigned'?: (boolean);
  '_bitWidth'?: "bitWidth";
  '_isUnsigned'?: "isUnsigned";
}

export interface BitIntType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'bitWidth'?: (number);
  'isUnsigned'?: (boolean);
  '_bitWidth'?: "bitWidth";
  '_isUnsigned'?: "isUnsigned";
}
