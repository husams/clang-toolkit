// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface VAArgExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'subexpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'resultType'?: (_ctk_ast_v1_QualType | null);
}

export interface VAArgExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'subexpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'resultType': (_ctk_ast_v1_QualType__Output | null);
}
