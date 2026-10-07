// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { APFloatBits as _ctk_ast_v1_APFloatBits, APFloatBits__Output as _ctk_ast_v1_APFloatBits__Output } from '../../../ctk/ast/v1/APFloatBits.js';

export interface FloatingLiteral {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'value'?: (_ctk_ast_v1_APFloatBits | null);
  'isExact'?: (boolean);
  '_isExact'?: "isExact";
}

export interface FloatingLiteral__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'value': (_ctk_ast_v1_APFloatBits__Output | null);
  'isExact'?: (boolean);
  '_isExact'?: "isExact";
}
