// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { CastExprInfo as _ctk_ast_v1_CastExprInfo, CastExprInfo__Output as _ctk_ast_v1_CastExprInfo__Output } from '../../../ctk/ast/v1/CastExprInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface CXXStaticCastExpr {
  'cast'?: (_ctk_ast_v1_CastExprInfo | null);
  'targetType'?: (_ctk_ast_v1_QualType | null);
}

export interface CXXStaticCastExpr__Output {
  'cast': (_ctk_ast_v1_CastExprInfo__Output | null);
  'targetType': (_ctk_ast_v1_QualType__Output | null);
}
