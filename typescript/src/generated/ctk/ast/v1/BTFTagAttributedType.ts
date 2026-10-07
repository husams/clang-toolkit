// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { AttributeValue as _ctk_ast_v1_AttributeValue, AttributeValue__Output as _ctk_ast_v1_AttributeValue__Output } from '../../../ctk/ast/v1/AttributeValue.js';

export interface BTFTagAttributedType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'wrappedType'?: (_ctk_ast_v1_QualType | null);
  'attribute'?: (_ctk_ast_v1_AttributeValue | null);
}

export interface BTFTagAttributedType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'wrappedType': (_ctk_ast_v1_QualType__Output | null);
  'attribute': (_ctk_ast_v1_AttributeValue__Output | null);
}
