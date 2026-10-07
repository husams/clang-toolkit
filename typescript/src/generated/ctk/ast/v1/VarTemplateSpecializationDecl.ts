// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { VarDeclInfo as _ctk_ast_v1_VarDeclInfo, VarDeclInfo__Output as _ctk_ast_v1_VarDeclInfo__Output } from '../../../ctk/ast/v1/VarDeclInfo.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { DeclTemplateSpecializationKind as _ctk_ast_v1_DeclTemplateSpecializationKind, DeclTemplateSpecializationKind__Output as _ctk_ast_v1_DeclTemplateSpecializationKind__Output } from '../../../ctk/ast/v1/DeclTemplateSpecializationKind.js';

export interface VarTemplateSpecializationDecl {
  'variable'?: (_ctk_ast_v1_VarDeclInfo | null);
  'templateArguments'?: (_ctk_ast_v1_TemplateArgument)[];
  'specializedTemplate'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'specializationKind'?: (_ctk_ast_v1_DeclTemplateSpecializationKind);
  '_specializationKind'?: "specializationKind";
}

export interface VarTemplateSpecializationDecl__Output {
  'variable': (_ctk_ast_v1_VarDeclInfo__Output | null);
  'templateArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
  'specializedTemplate': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'specializationKind'?: (_ctk_ast_v1_DeclTemplateSpecializationKind__Output);
  '_specializationKind'?: "specializationKind";
}
