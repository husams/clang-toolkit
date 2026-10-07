// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { UnaryExprTrait as _ctk_ast_v1_UnaryExprTrait, UnaryExprTrait__Output as _ctk_ast_v1_UnaryExprTrait__Output } from '../../../ctk/ast/v1/UnaryExprTrait.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface UnaryExprOrTypeTraitExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'trait'?: (_ctk_ast_v1_UnaryExprTrait);
  'argumentExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'argumentType'?: (_ctk_ast_v1_QualType | null);
  'isTypeArgument'?: (boolean);
  '_trait'?: "trait";
  '_isTypeArgument'?: "isTypeArgument";
}

export interface UnaryExprOrTypeTraitExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'trait'?: (_ctk_ast_v1_UnaryExprTrait__Output);
  'argumentExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'argumentType': (_ctk_ast_v1_QualType__Output | null);
  'isTypeArgument'?: (boolean);
  '_trait'?: "trait";
  '_isTypeArgument'?: "isTypeArgument";
}
