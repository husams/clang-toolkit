// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';
import type { DeclarationName as _ctk_ast_v1_DeclarationName, DeclarationName__Output as _ctk_ast_v1_DeclarationName__Output } from '../../../ctk/ast/v1/DeclarationName.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface DependentScopeDeclRefExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
  'name'?: (_ctk_ast_v1_DeclarationName | null);
  'templateArguments'?: (_ctk_ast_v1_TemplateArgument)[];
}

export interface DependentScopeDeclRefExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
  'name': (_ctk_ast_v1_DeclarationName__Output | null);
  'templateArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
}
