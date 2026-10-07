// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';
import type { DeclarationName as _ctk_ast_v1_DeclarationName, DeclarationName__Output as _ctk_ast_v1_DeclarationName__Output } from '../../../ctk/ast/v1/DeclarationName.js';

export interface DependentTemplateName {
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
  'name'?: (_ctk_ast_v1_DeclarationName | null);
}

export interface DependentTemplateName__Output {
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
  'name': (_ctk_ast_v1_DeclarationName__Output | null);
}
