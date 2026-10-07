// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { UnaryOpcode as _ctk_ast_v1_UnaryOpcode, UnaryOpcode__Output as _ctk_ast_v1_UnaryOpcode__Output } from '../../../ctk/ast/v1/UnaryOpcode.js';

export interface UnaryOperator {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'operand'?: (_ctk_ast_v1_ExpressionValue | null);
  'opcode'?: (_ctk_ast_v1_UnaryOpcode);
  'isPostfix'?: (boolean);
  '_opcode'?: "opcode";
  '_isPostfix'?: "isPostfix";
}

export interface UnaryOperator__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'operand': (_ctk_ast_v1_ExpressionValue__Output | null);
  'opcode'?: (_ctk_ast_v1_UnaryOpcode__Output);
  'isPostfix'?: (boolean);
  '_opcode'?: "opcode";
  '_isPostfix'?: "isPostfix";
}
