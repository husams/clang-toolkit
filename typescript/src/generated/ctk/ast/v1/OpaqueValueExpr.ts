// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface OpaqueValueExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'sourceExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'opaqueType'?: (_ctk_ast_v1_QualType | null);
}

export interface OpaqueValueExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'sourceExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'opaqueType': (_ctk_ast_v1_QualType__Output | null);
}
