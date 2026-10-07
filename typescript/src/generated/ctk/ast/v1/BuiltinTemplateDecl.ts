// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { DeclBuiltinTemplateKind as _ctk_ast_v1_DeclBuiltinTemplateKind, DeclBuiltinTemplateKind__Output as _ctk_ast_v1_DeclBuiltinTemplateKind__Output } from '../../../ctk/ast/v1/DeclBuiltinTemplateKind.js';
import type { TemplateParameterList as _ctk_ast_v1_TemplateParameterList, TemplateParameterList__Output as _ctk_ast_v1_TemplateParameterList__Output } from '../../../ctk/ast/v1/TemplateParameterList.js';

export interface BuiltinTemplateDecl {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'builtinKind'?: (_ctk_ast_v1_DeclBuiltinTemplateKind);
  'templateParameters'?: (_ctk_ast_v1_TemplateParameterList | null);
  '_builtinKind'?: "builtinKind";
}

export interface BuiltinTemplateDecl__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'builtinKind'?: (_ctk_ast_v1_DeclBuiltinTemplateKind__Output);
  'templateParameters': (_ctk_ast_v1_TemplateParameterList__Output | null);
  '_builtinKind'?: "builtinKind";
}
