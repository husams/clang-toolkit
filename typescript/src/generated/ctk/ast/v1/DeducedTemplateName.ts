// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TemplateName as _ctk_ast_v1_TemplateName, TemplateName__Output as _ctk_ast_v1_TemplateName__Output } from '../../../ctk/ast/v1/TemplateName.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface DeducedTemplateName {
  'underlying'?: (_ctk_ast_v1_TemplateName | null);
  'defaultArguments'?: (_ctk_ast_v1_TemplateArgument)[];
  'defaultArgumentStart'?: (number);
  '_defaultArgumentStart'?: "defaultArgumentStart";
}

export interface DeducedTemplateName__Output {
  'underlying': (_ctk_ast_v1_TemplateName__Output | null);
  'defaultArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
  'defaultArgumentStart'?: (number);
  '_defaultArgumentStart'?: "defaultArgumentStart";
}
