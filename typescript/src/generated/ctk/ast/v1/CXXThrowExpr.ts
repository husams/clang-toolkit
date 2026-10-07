// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CXXThrowExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'operand'?: (_ctk_ast_v1_ExpressionValue | null);
  'isRethrow'?: (boolean);
  '_isRethrow'?: "isRethrow";
}

export interface CXXThrowExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'operand': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isRethrow'?: (boolean);
  '_isRethrow'?: "isRethrow";
}
