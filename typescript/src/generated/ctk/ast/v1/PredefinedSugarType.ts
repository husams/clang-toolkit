// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { PredefinedTypeKind as _ctk_ast_v1_PredefinedTypeKind, PredefinedTypeKind__Output as _ctk_ast_v1_PredefinedTypeKind__Output } from '../../../ctk/ast/v1/PredefinedTypeKind.js';

export interface PredefinedSugarType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'predefinedKind'?: (_ctk_ast_v1_PredefinedTypeKind);
  'identifier'?: (string);
  '_predefinedKind'?: "predefinedKind";
  '_identifier'?: "identifier";
}

export interface PredefinedSugarType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'predefinedKind'?: (_ctk_ast_v1_PredefinedTypeKind__Output);
  'identifier'?: (string);
  '_predefinedKind'?: "predefinedKind";
  '_identifier'?: "identifier";
}
