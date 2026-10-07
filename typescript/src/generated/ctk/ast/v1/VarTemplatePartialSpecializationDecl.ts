// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { VarDeclInfo as _ctk_ast_v1_VarDeclInfo, VarDeclInfo__Output as _ctk_ast_v1_VarDeclInfo__Output } from '../../../ctk/ast/v1/VarDeclInfo.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';
import type { TemplateParameterList as _ctk_ast_v1_TemplateParameterList, TemplateParameterList__Output as _ctk_ast_v1_TemplateParameterList__Output } from '../../../ctk/ast/v1/TemplateParameterList.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface VarTemplatePartialSpecializationDecl {
  'variable'?: (_ctk_ast_v1_VarDeclInfo | null);
  'templateArguments'?: (_ctk_ast_v1_TemplateArgument)[];
  'templateParameters'?: (_ctk_ast_v1_TemplateParameterList | null);
  'specializedTemplate'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'specializedTemplateOrPartial'?: (_ctk_ast_v1_DeclarationSymbol | null);
}

export interface VarTemplatePartialSpecializationDecl__Output {
  'variable': (_ctk_ast_v1_VarDeclInfo__Output | null);
  'templateArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
  'templateParameters': (_ctk_ast_v1_TemplateParameterList__Output | null);
  'specializedTemplate': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'specializedTemplateOrPartial': (_ctk_ast_v1_DeclarationSymbol__Output | null);
}
