// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { RecordDeclInfo as _ctk_ast_v1_RecordDeclInfo, RecordDeclInfo__Output as _ctk_ast_v1_RecordDeclInfo__Output } from '../../../ctk/ast/v1/RecordDeclInfo.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';
import type { TemplateParameterList as _ctk_ast_v1_TemplateParameterList, TemplateParameterList__Output as _ctk_ast_v1_TemplateParameterList__Output } from '../../../ctk/ast/v1/TemplateParameterList.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface ClassTemplatePartialSpecializationDecl {
  'record'?: (_ctk_ast_v1_RecordDeclInfo | null);
  'templateArguments'?: (_ctk_ast_v1_TemplateArgument)[];
  'templateParameters'?: (_ctk_ast_v1_TemplateParameterList | null);
  'specializedTemplate'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'specializedTemplateOrPartial'?: (_ctk_ast_v1_DeclarationSymbol | null);
}

export interface ClassTemplatePartialSpecializationDecl__Output {
  'record': (_ctk_ast_v1_RecordDeclInfo__Output | null);
  'templateArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
  'templateParameters': (_ctk_ast_v1_TemplateParameterList__Output | null);
  'specializedTemplate': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'specializedTemplateOrPartial': (_ctk_ast_v1_DeclarationSymbol__Output | null);
}
