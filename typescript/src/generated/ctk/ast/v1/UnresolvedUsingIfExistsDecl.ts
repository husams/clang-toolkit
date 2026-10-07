// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';
import type { DeclarationName as _ctk_ast_v1_DeclarationName, DeclarationName__Output as _ctk_ast_v1_DeclarationName__Output } from '../../../ctk/ast/v1/DeclarationName.js';

export interface UnresolvedUsingIfExistsDecl {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
  'targetName'?: (_ctk_ast_v1_DeclarationName | null);
}

export interface UnresolvedUsingIfExistsDecl__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
  'targetName': (_ctk_ast_v1_DeclarationName__Output | null);
}
