// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { RecordDeclInfo as _ctk_ast_v1_RecordDeclInfo, RecordDeclInfo__Output as _ctk_ast_v1_RecordDeclInfo__Output } from '../../../ctk/ast/v1/RecordDeclInfo.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { DeclTemplateSpecializationKind as _ctk_ast_v1_DeclTemplateSpecializationKind, DeclTemplateSpecializationKind__Output as _ctk_ast_v1_DeclTemplateSpecializationKind__Output } from '../../../ctk/ast/v1/DeclTemplateSpecializationKind.js';

export interface ClassTemplateSpecializationDecl {
  'record'?: (_ctk_ast_v1_RecordDeclInfo | null);
  'templateArguments'?: (_ctk_ast_v1_TemplateArgument)[];
  'specializedTemplate'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'specializationKind'?: (_ctk_ast_v1_DeclTemplateSpecializationKind);
  '_specializationKind'?: "specializationKind";
}

export interface ClassTemplateSpecializationDecl__Output {
  'record': (_ctk_ast_v1_RecordDeclInfo__Output | null);
  'templateArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
  'specializedTemplate': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'specializationKind'?: (_ctk_ast_v1_DeclTemplateSpecializationKind__Output);
  '_specializationKind'?: "specializationKind";
}
