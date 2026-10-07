// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface ChooseExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'condition'?: (_ctk_ast_v1_ExpressionValue | null);
  'leftExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'rightExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'isConditionTrue'?: (boolean);
  '_isConditionTrue'?: "isConditionTrue";
}

export interface ChooseExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'condition': (_ctk_ast_v1_ExpressionValue__Output | null);
  'leftExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'rightExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isConditionTrue'?: (boolean);
  '_isConditionTrue'?: "isConditionTrue";
}
