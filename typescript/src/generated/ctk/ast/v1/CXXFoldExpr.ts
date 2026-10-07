// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { BinaryOpcode as _ctk_ast_v1_BinaryOpcode, BinaryOpcode__Output as _ctk_ast_v1_BinaryOpcode__Output } from '../../../ctk/ast/v1/BinaryOpcode.js';

export interface CXXFoldExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'pattern'?: (_ctk_ast_v1_ExpressionValue | null);
  'leftOperand'?: (_ctk_ast_v1_ExpressionValue | null);
  'rightOperand'?: (_ctk_ast_v1_ExpressionValue | null);
  'operatorKind'?: (_ctk_ast_v1_BinaryOpcode);
  'isLeftFold'?: (boolean);
  '_operatorKind'?: "operatorKind";
  '_isLeftFold'?: "isLeftFold";
}

export interface CXXFoldExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'pattern': (_ctk_ast_v1_ExpressionValue__Output | null);
  'leftOperand': (_ctk_ast_v1_ExpressionValue__Output | null);
  'rightOperand': (_ctk_ast_v1_ExpressionValue__Output | null);
  'operatorKind'?: (_ctk_ast_v1_BinaryOpcode__Output);
  'isLeftFold'?: (boolean);
  '_operatorKind'?: "operatorKind";
  '_isLeftFold'?: "isLeftFold";
}
