// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { TypeOfKind as _ctk_ast_v1_TypeOfKind, TypeOfKind__Output as _ctk_ast_v1_TypeOfKind__Output } from '../../../ctk/ast/v1/TypeOfKind.js';

export interface TypeOfType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'underlyingType'?: (_ctk_ast_v1_QualType | null);
  'kind'?: (_ctk_ast_v1_TypeOfKind);
  '_kind'?: "kind";
}

export interface TypeOfType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'underlyingType': (_ctk_ast_v1_QualType__Output | null);
  'kind'?: (_ctk_ast_v1_TypeOfKind__Output);
  '_kind'?: "kind";
}
