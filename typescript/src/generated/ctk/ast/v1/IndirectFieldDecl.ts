// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ValueDeclInfo as _ctk_ast_v1_ValueDeclInfo, ValueDeclInfo__Output as _ctk_ast_v1_ValueDeclInfo__Output } from '../../../ctk/ast/v1/ValueDeclInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface IndirectFieldDecl {
  'value'?: (_ctk_ast_v1_ValueDeclInfo | null);
  'chain'?: (_ctk_ast_v1_DeclarationSymbol)[];
}

export interface IndirectFieldDecl__Output {
  'value': (_ctk_ast_v1_ValueDeclInfo__Output | null);
  'chain': (_ctk_ast_v1_DeclarationSymbol__Output)[];
}
