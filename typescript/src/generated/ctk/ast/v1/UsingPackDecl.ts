// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface UsingPackDecl {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'usingDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'expansions'?: (_ctk_ast_v1_DeclarationSymbol)[];
}

export interface UsingPackDecl__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'usingDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'expansions': (_ctk_ast_v1_DeclarationSymbol__Output)[];
}
