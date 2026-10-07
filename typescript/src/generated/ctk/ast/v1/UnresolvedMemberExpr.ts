// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { DeclarationName as _ctk_ast_v1_DeclarationName, DeclarationName__Output as _ctk_ast_v1_DeclarationName__Output } from '../../../ctk/ast/v1/DeclarationName.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface UnresolvedMemberExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'base'?: (_ctk_ast_v1_ExpressionValue | null);
  'name'?: (_ctk_ast_v1_DeclarationName | null);
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
  'candidateDeclarations'?: (_ctk_ast_v1_DeclarationSymbol)[];
  'isArrow'?: (boolean);
  'isUnqualified'?: (boolean);
  'templateArguments'?: (_ctk_ast_v1_TemplateArgument)[];
  '_isArrow'?: "isArrow";
  '_isUnqualified'?: "isUnqualified";
}

export interface UnresolvedMemberExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'base': (_ctk_ast_v1_ExpressionValue__Output | null);
  'name': (_ctk_ast_v1_DeclarationName__Output | null);
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
  'candidateDeclarations': (_ctk_ast_v1_DeclarationSymbol__Output)[];
  'isArrow'?: (boolean);
  'isUnqualified'?: (boolean);
  'templateArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
  '_isArrow'?: "isArrow";
  '_isUnqualified'?: "isUnqualified";
}
