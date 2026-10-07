// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ValueDeclInfo as _ctk_ast_v1_ValueDeclInfo, ValueDeclInfo__Output as _ctk_ast_v1_ValueDeclInfo__Output } from '../../../ctk/ast/v1/ValueDeclInfo.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';
import type { DeclarationName as _ctk_ast_v1_DeclarationName, DeclarationName__Output as _ctk_ast_v1_DeclarationName__Output } from '../../../ctk/ast/v1/DeclarationName.js';

export interface UnresolvedUsingValueDecl {
  'value'?: (_ctk_ast_v1_ValueDeclInfo | null);
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
  'targetName'?: (_ctk_ast_v1_DeclarationName | null);
}

export interface UnresolvedUsingValueDecl__Output {
  'value': (_ctk_ast_v1_ValueDeclInfo__Output | null);
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
  'targetName': (_ctk_ast_v1_DeclarationName__Output | null);
}
