// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { AttributedTypeKind as _ctk_ast_v1_AttributedTypeKind, AttributedTypeKind__Output as _ctk_ast_v1_AttributedTypeKind__Output } from '../../../ctk/ast/v1/AttributedTypeKind.js';
import type { AttributeValue as _ctk_ast_v1_AttributeValue, AttributeValue__Output as _ctk_ast_v1_AttributeValue__Output } from '../../../ctk/ast/v1/AttributeValue.js';

export interface AttributedType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'modifiedType'?: (_ctk_ast_v1_QualType | null);
  'equivalentType'?: (_ctk_ast_v1_QualType | null);
  'attributeKind'?: (_ctk_ast_v1_AttributedTypeKind);
  'attribute'?: (_ctk_ast_v1_AttributeValue | null);
  'attributeKindName'?: (string);
  '_attributeKind'?: "attributeKind";
  '_attributeKindName'?: "attributeKindName";
}

export interface AttributedType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'modifiedType': (_ctk_ast_v1_QualType__Output | null);
  'equivalentType': (_ctk_ast_v1_QualType__Output | null);
  'attributeKind'?: (_ctk_ast_v1_AttributedTypeKind__Output);
  'attribute': (_ctk_ast_v1_AttributeValue__Output | null);
  'attributeKindName'?: (string);
  '_attributeKind'?: "attributeKind";
  '_attributeKindName'?: "attributeKindName";
}
