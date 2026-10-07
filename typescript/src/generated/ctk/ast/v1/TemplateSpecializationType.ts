// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { TemplateName as _ctk_ast_v1_TemplateName, TemplateName__Output as _ctk_ast_v1_TemplateName__Output } from '../../../ctk/ast/v1/TemplateName.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface TemplateSpecializationType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'templateName'?: (_ctk_ast_v1_TemplateName | null);
  'arguments'?: (_ctk_ast_v1_TemplateArgument)[];
  'aliasedType'?: (_ctk_ast_v1_QualType | null);
  'hasAlias'?: (boolean);
  '_hasAlias'?: "hasAlias";
}

export interface TemplateSpecializationType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'templateName': (_ctk_ast_v1_TemplateName__Output | null);
  'arguments': (_ctk_ast_v1_TemplateArgument__Output)[];
  'aliasedType': (_ctk_ast_v1_QualType__Output | null);
  'hasAlias'?: (boolean);
  '_hasAlias'?: "hasAlias";
}
