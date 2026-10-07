// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { VectorKind as _ctk_ast_v1_VectorKind, VectorKind__Output as _ctk_ast_v1_VectorKind__Output } from '../../../ctk/ast/v1/VectorKind.js';

export interface VectorType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'elementType'?: (_ctk_ast_v1_QualType | null);
  'elementCount'?: (number);
  'vectorKind'?: (_ctk_ast_v1_VectorKind);
  '_elementCount'?: "elementCount";
  '_vectorKind'?: "vectorKind";
}

export interface VectorType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'elementType': (_ctk_ast_v1_QualType__Output | null);
  'elementCount'?: (number);
  'vectorKind'?: (_ctk_ast_v1_VectorKind__Output);
  '_elementCount'?: "elementCount";
  '_vectorKind'?: "vectorKind";
}
