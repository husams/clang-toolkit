// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { AtomicOpcode as _ctk_ast_v1_AtomicOpcode, AtomicOpcode__Output as _ctk_ast_v1_AtomicOpcode__Output } from '../../../ctk/ast/v1/AtomicOpcode.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface AtomicExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'opcode'?: (_ctk_ast_v1_AtomicOpcode);
  'arguments'?: (_ctk_ast_v1_ExpressionValue)[];
  'opcodeName'?: (string);
  '_opcode'?: "opcode";
  '_opcodeName'?: "opcodeName";
}

export interface AtomicExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'opcode'?: (_ctk_ast_v1_AtomicOpcode__Output);
  'arguments': (_ctk_ast_v1_ExpressionValue__Output)[];
  'opcodeName'?: (string);
  '_opcode'?: "opcode";
  '_opcodeName'?: "opcodeName";
}
