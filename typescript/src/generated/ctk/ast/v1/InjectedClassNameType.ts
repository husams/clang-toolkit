// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';
import type { TemplateName as _ctk_ast_v1_TemplateName, TemplateName__Output as _ctk_ast_v1_TemplateName__Output } from '../../../ctk/ast/v1/TemplateName.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface InjectedClassNameType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
  'templateDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'templateName'?: (_ctk_ast_v1_TemplateName | null);
  'specializationArguments'?: (_ctk_ast_v1_TemplateArgument)[];
}

export interface InjectedClassNameType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'declaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
  'templateDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'templateName': (_ctk_ast_v1_TemplateName__Output | null);
  'specializationArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
}
