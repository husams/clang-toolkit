// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionTrait as _ctk_ast_v1_ExpressionTrait, ExpressionTrait__Output as _ctk_ast_v1_ExpressionTrait__Output } from '../../../ctk/ast/v1/ExpressionTrait.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface ExpressionTraitExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'trait'?: (_ctk_ast_v1_ExpressionTrait);
  'queriedExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'traitValue'?: (boolean);
  '_trait'?: "trait";
  '_traitValue'?: "traitValue";
}

export interface ExpressionTraitExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'trait'?: (_ctk_ast_v1_ExpressionTrait__Output);
  'queriedExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'traitValue'?: (boolean);
  '_trait'?: "trait";
  '_traitValue'?: "traitValue";
}
