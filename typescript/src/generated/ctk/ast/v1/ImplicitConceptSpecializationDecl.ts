// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface ImplicitConceptSpecializationDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'templateArguments'?: (_ctk_ast_v1_TemplateArgument)[];
}

export interface ImplicitConceptSpecializationDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'templateArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
}
