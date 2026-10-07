// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { BuiltinKind as _ctk_ast_v1_BuiltinKind, BuiltinKind__Output as _ctk_ast_v1_BuiltinKind__Output } from '../../../ctk/ast/v1/BuiltinKind.js';

export interface BuiltinType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'kind'?: (_ctk_ast_v1_BuiltinKind);
  'extendedKindName'?: (string);
  '_kind'?: "kind";
  '_extendedKindName'?: "extendedKindName";
}

export interface BuiltinType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'kind'?: (_ctk_ast_v1_BuiltinKind__Output);
  'extendedKindName'?: (string);
  '_kind'?: "kind";
  '_extendedKindName'?: "extendedKindName";
}
