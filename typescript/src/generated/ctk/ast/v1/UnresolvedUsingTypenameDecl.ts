// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeDeclInfo as _ctk_ast_v1_TypeDeclInfo, TypeDeclInfo__Output as _ctk_ast_v1_TypeDeclInfo__Output } from '../../../ctk/ast/v1/TypeDeclInfo.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';
import type { DeclarationName as _ctk_ast_v1_DeclarationName, DeclarationName__Output as _ctk_ast_v1_DeclarationName__Output } from '../../../ctk/ast/v1/DeclarationName.js';

export interface UnresolvedUsingTypenameDecl {
  'typeDeclaration'?: (_ctk_ast_v1_TypeDeclInfo | null);
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
  'targetName'?: (_ctk_ast_v1_DeclarationName | null);
}

export interface UnresolvedUsingTypenameDecl__Output {
  'typeDeclaration': (_ctk_ast_v1_TypeDeclInfo__Output | null);
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
  'targetName': (_ctk_ast_v1_DeclarationName__Output | null);
}
