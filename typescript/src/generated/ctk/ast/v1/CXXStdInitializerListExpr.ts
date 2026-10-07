// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CXXStdInitializerListExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'subexpression'?: (_ctk_ast_v1_ExpressionValue | null);
}

export interface CXXStdInitializerListExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'subexpression': (_ctk_ast_v1_ExpressionValue__Output | null);
}
