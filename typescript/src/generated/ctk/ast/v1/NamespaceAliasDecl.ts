// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';

export interface NamespaceAliasDecl {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'namespaceDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'aliasedNamespace'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
}

export interface NamespaceAliasDecl__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'namespaceDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'aliasedNamespace': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
}
