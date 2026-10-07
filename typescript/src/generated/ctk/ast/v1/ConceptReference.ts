// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';
import type { DeclarationName as _ctk_ast_v1_DeclarationName, DeclarationName__Output as _ctk_ast_v1_DeclarationName__Output } from '../../../ctk/ast/v1/DeclarationName.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface ConceptReference {
  'conceptDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'foundDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
  'name'?: (_ctk_ast_v1_DeclarationName | null);
  'arguments'?: (_ctk_ast_v1_TemplateArgument)[];
}

export interface ConceptReference__Output {
  'conceptDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'foundDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
  'name': (_ctk_ast_v1_DeclarationName__Output | null);
  'arguments': (_ctk_ast_v1_TemplateArgument__Output)[];
}
