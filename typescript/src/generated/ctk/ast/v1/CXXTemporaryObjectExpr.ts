// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { CXXConstructExprInfo as _ctk_ast_v1_CXXConstructExprInfo, CXXConstructExprInfo__Output as _ctk_ast_v1_CXXConstructExprInfo__Output } from '../../../ctk/ast/v1/CXXConstructExprInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface CXXTemporaryObjectExpr {
  'construction'?: (_ctk_ast_v1_CXXConstructExprInfo | null);
  'targetType'?: (_ctk_ast_v1_QualType | null);
}

export interface CXXTemporaryObjectExpr__Output {
  'construction': (_ctk_ast_v1_CXXConstructExprInfo__Output | null);
  'targetType': (_ctk_ast_v1_QualType__Output | null);
}
