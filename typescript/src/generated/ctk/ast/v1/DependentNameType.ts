// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';

export interface DependentNameType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
  'identifier'?: (string);
  '_identifier'?: "identifier";
}

export interface DependentNameType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
  'identifier'?: (string);
  '_identifier'?: "identifier";
}
