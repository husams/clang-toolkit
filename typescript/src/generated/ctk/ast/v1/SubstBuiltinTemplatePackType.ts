// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface SubstBuiltinTemplatePackType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'argumentPack'?: (_ctk_ast_v1_TemplateArgument | null);
}

export interface SubstBuiltinTemplatePackType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'argumentPack': (_ctk_ast_v1_TemplateArgument__Output | null);
}
