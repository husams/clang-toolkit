// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { UnaryTransformKind as _ctk_ast_v1_UnaryTransformKind, UnaryTransformKind__Output as _ctk_ast_v1_UnaryTransformKind__Output } from '../../../ctk/ast/v1/UnaryTransformKind.js';

export interface UnaryTransformType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'baseType'?: (_ctk_ast_v1_QualType | null);
  'transformedType'?: (_ctk_ast_v1_QualType | null);
  'transformKind'?: (_ctk_ast_v1_UnaryTransformKind);
  '_transformKind'?: "transformKind";
}

export interface UnaryTransformType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'baseType': (_ctk_ast_v1_QualType__Output | null);
  'transformedType': (_ctk_ast_v1_QualType__Output | null);
  'transformKind'?: (_ctk_ast_v1_UnaryTransformKind__Output);
  '_transformKind'?: "transformKind";
}
