// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface CXXScalarValueInitExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'targetType'?: (_ctk_ast_v1_QualType | null);
}

export interface CXXScalarValueInitExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'targetType': (_ctk_ast_v1_QualType__Output | null);
}
