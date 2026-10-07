// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { BinaryOpcode as _ctk_ast_v1_BinaryOpcode, BinaryOpcode__Output as _ctk_ast_v1_BinaryOpcode__Output } from '../../../ctk/ast/v1/BinaryOpcode.js';

export interface BinaryOperator {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'left'?: (_ctk_ast_v1_ExpressionValue | null);
  'right'?: (_ctk_ast_v1_ExpressionValue | null);
  'opcode'?: (_ctk_ast_v1_BinaryOpcode);
  'isCompoundAssignment'?: (boolean);
  '_opcode'?: "opcode";
  '_isCompoundAssignment'?: "isCompoundAssignment";
}

export interface BinaryOperator__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'left': (_ctk_ast_v1_ExpressionValue__Output | null);
  'right': (_ctk_ast_v1_ExpressionValue__Output | null);
  'opcode'?: (_ctk_ast_v1_BinaryOpcode__Output);
  'isCompoundAssignment'?: (boolean);
  '_opcode'?: "opcode";
  '_isCompoundAssignment'?: "isCompoundAssignment";
}
