// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CompoundLiteralExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'literalType'?: (_ctk_ast_v1_QualType | null);
  'initializer'?: (_ctk_ast_v1_ExpressionValue | null);
  'isFileScope'?: (boolean);
  '_isFileScope'?: "isFileScope";
}

export interface CompoundLiteralExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'literalType': (_ctk_ast_v1_QualType__Output | null);
  'initializer': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isFileScope'?: (boolean);
  '_isFileScope'?: "isFileScope";
}
