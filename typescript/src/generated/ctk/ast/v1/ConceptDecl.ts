// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { TemplateParameterList as _ctk_ast_v1_TemplateParameterList, TemplateParameterList__Output as _ctk_ast_v1_TemplateParameterList__Output } from '../../../ctk/ast/v1/TemplateParameterList.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface ConceptDecl {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'templateParameters'?: (_ctk_ast_v1_TemplateParameterList | null);
  'constraintExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'isTypeConcept'?: (boolean);
  'hasDefinition'?: (boolean);
  '_isTypeConcept'?: "isTypeConcept";
  '_hasDefinition'?: "hasDefinition";
}

export interface ConceptDecl__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'templateParameters': (_ctk_ast_v1_TemplateParameterList__Output | null);
  'constraintExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isTypeConcept'?: (boolean);
  'hasDefinition'?: (boolean);
  '_isTypeConcept'?: "isTypeConcept";
  '_hasDefinition'?: "hasDefinition";
}
