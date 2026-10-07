// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';
import type { TemplateName as _ctk_ast_v1_TemplateName, TemplateName__Output as _ctk_ast_v1_TemplateName__Output } from '../../../ctk/ast/v1/TemplateName.js';

export interface QualifiedTemplateName {
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
  'unqualified'?: (_ctk_ast_v1_TemplateName | null);
}

export interface QualifiedTemplateName__Output {
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
  'unqualified': (_ctk_ast_v1_TemplateName__Output | null);
}
