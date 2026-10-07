// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { Empty as _ctk_ast_v1_Empty, Empty__Output as _ctk_ast_v1_Empty__Output } from '../../../ctk/ast/v1/Empty.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { DeclarationTemplateArgument as _ctk_ast_v1_DeclarationTemplateArgument, DeclarationTemplateArgument__Output as _ctk_ast_v1_DeclarationTemplateArgument__Output } from '../../../ctk/ast/v1/DeclarationTemplateArgument.js';
import type { IntegralTemplateArgument as _ctk_ast_v1_IntegralTemplateArgument, IntegralTemplateArgument__Output as _ctk_ast_v1_IntegralTemplateArgument__Output } from '../../../ctk/ast/v1/IntegralTemplateArgument.js';
import type { StructuralTemplateArgument as _ctk_ast_v1_StructuralTemplateArgument, StructuralTemplateArgument__Output as _ctk_ast_v1_StructuralTemplateArgument__Output } from '../../../ctk/ast/v1/StructuralTemplateArgument.js';
import type { TemplateName as _ctk_ast_v1_TemplateName, TemplateName__Output as _ctk_ast_v1_TemplateName__Output } from '../../../ctk/ast/v1/TemplateName.js';
import type { TemplateExpansionArgument as _ctk_ast_v1_TemplateExpansionArgument, TemplateExpansionArgument__Output as _ctk_ast_v1_TemplateExpansionArgument__Output } from '../../../ctk/ast/v1/TemplateExpansionArgument.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { TemplateArgumentPack as _ctk_ast_v1_TemplateArgumentPack, TemplateArgumentPack__Output as _ctk_ast_v1_TemplateArgumentPack__Output } from '../../../ctk/ast/v1/TemplateArgumentPack.js';

export interface TemplateArgument {
  'nullArgument'?: (_ctk_ast_v1_Empty | null);
  'type'?: (_ctk_ast_v1_QualType | null);
  'declaration'?: (_ctk_ast_v1_DeclarationTemplateArgument | null);
  'nullPointerType'?: (_ctk_ast_v1_QualType | null);
  'integral'?: (_ctk_ast_v1_IntegralTemplateArgument | null);
  'structuralValue'?: (_ctk_ast_v1_StructuralTemplateArgument | null);
  'templateName'?: (_ctk_ast_v1_TemplateName | null);
  'templateExpansion'?: (_ctk_ast_v1_TemplateExpansionArgument | null);
  'expression'?: (_ctk_ast_v1_ExpressionValue | null);
  'pack'?: (_ctk_ast_v1_TemplateArgumentPack | null);
  'value'?: "nullArgument"|"type"|"declaration"|"nullPointerType"|"integral"|"structuralValue"|"templateName"|"templateExpansion"|"expression"|"pack";
}

export interface TemplateArgument__Output {
  'nullArgument'?: (_ctk_ast_v1_Empty__Output | null);
  'type'?: (_ctk_ast_v1_QualType__Output | null);
  'declaration'?: (_ctk_ast_v1_DeclarationTemplateArgument__Output | null);
  'nullPointerType'?: (_ctk_ast_v1_QualType__Output | null);
  'integral'?: (_ctk_ast_v1_IntegralTemplateArgument__Output | null);
  'structuralValue'?: (_ctk_ast_v1_StructuralTemplateArgument__Output | null);
  'templateName'?: (_ctk_ast_v1_TemplateName__Output | null);
  'templateExpansion'?: (_ctk_ast_v1_TemplateExpansionArgument__Output | null);
  'expression'?: (_ctk_ast_v1_ExpressionValue__Output | null);
  'pack'?: (_ctk_ast_v1_TemplateArgumentPack__Output | null);
  'value'?: "nullArgument"|"type"|"declaration"|"nullPointerType"|"integral"|"structuralValue"|"templateName"|"templateExpansion"|"expression"|"pack";
}
