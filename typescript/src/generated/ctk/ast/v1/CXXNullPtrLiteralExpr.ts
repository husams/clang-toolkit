// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';

export interface CXXNullPtrLiteralExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'isNullPointerConstant'?: (boolean);
  '_isNullPointerConstant'?: "isNullPointerConstant";
}

export interface CXXNullPtrLiteralExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'isNullPointerConstant'?: (boolean);
  '_isNullPointerConstant'?: "isNullPointerConstant";
}
