// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { TemplateParameterList as _ctk_ast_v1_TemplateParameterList, TemplateParameterList__Output as _ctk_ast_v1_TemplateParameterList__Output } from '../../../ctk/ast/v1/TemplateParameterList.js';

export interface TypeAliasTemplateDecl {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'templatedDeclaration'?: (_ctk_ast_v1_DeclarationValue | null);
  'templateParameters'?: (_ctk_ast_v1_TemplateParameterList | null);
}

export interface TypeAliasTemplateDecl__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'templatedDeclaration': (_ctk_ast_v1_DeclarationValue__Output | null);
  'templateParameters': (_ctk_ast_v1_TemplateParameterList__Output | null);
}
