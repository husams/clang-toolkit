// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface UsingShadowDecl {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'targetDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'introducer'?: (_ctk_ast_v1_DeclarationSymbol | null);
}

export interface UsingShadowDecl__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'targetDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'introducer': (_ctk_ast_v1_DeclarationSymbol__Output | null);
}
