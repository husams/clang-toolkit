// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface DesignatedInitUpdateExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'base'?: (_ctk_ast_v1_ExpressionValue | null);
  'updateExpression'?: (_ctk_ast_v1_ExpressionValue | null);
}

export interface DesignatedInitUpdateExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'base': (_ctk_ast_v1_ExpressionValue__Output | null);
  'updateExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
}
