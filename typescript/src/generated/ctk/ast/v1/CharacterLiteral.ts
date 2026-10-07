// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { CharacterKind as _ctk_ast_v1_CharacterKind, CharacterKind__Output as _ctk_ast_v1_CharacterKind__Output } from '../../../ctk/ast/v1/CharacterKind.js';

export interface CharacterLiteral {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'value'?: (number);
  'characterKind'?: (_ctk_ast_v1_CharacterKind);
  '_value'?: "value";
  '_characterKind'?: "characterKind";
}

export interface CharacterLiteral__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'value'?: (number);
  'characterKind'?: (_ctk_ast_v1_CharacterKind__Output);
  '_value'?: "value";
  '_characterKind'?: "characterKind";
}
