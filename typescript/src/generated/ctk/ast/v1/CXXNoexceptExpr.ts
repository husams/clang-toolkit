// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CXXNoexceptExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'operand'?: (_ctk_ast_v1_ExpressionValue | null);
  'value'?: (boolean);
  'isValueDependent'?: (boolean);
  '_value'?: "value";
  '_isValueDependent'?: "isValueDependent";
}

export interface CXXNoexceptExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'operand': (_ctk_ast_v1_ExpressionValue__Output | null);
  'value'?: (boolean);
  'isValueDependent'?: (boolean);
  '_value'?: "value";
  '_isValueDependent'?: "isValueDependent";
}
