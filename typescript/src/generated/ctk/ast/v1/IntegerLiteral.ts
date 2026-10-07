// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { APIntBits as _ctk_ast_v1_APIntBits, APIntBits__Output as _ctk_ast_v1_APIntBits__Output } from '../../../ctk/ast/v1/APIntBits.js';

export interface IntegerLiteral {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'value'?: (_ctk_ast_v1_APIntBits | null);
}

export interface IntegerLiteral__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'value': (_ctk_ast_v1_APIntBits__Output | null);
}
