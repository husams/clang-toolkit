// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { APIntBits as _ctk_ast_v1_APIntBits, APIntBits__Output as _ctk_ast_v1_APIntBits__Output } from '../../../ctk/ast/v1/APIntBits.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { ArraySizeModifier as _ctk_ast_v1_ArraySizeModifier, ArraySizeModifier__Output as _ctk_ast_v1_ArraySizeModifier__Output } from '../../../ctk/ast/v1/ArraySizeModifier.js';
import type { Qualifiers as _ctk_ast_v1_Qualifiers, Qualifiers__Output as _ctk_ast_v1_Qualifiers__Output } from '../../../ctk/ast/v1/Qualifiers.js';

export interface ConstantArrayType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'elementType'?: (_ctk_ast_v1_QualType | null);
  'size'?: (_ctk_ast_v1_APIntBits | null);
  'sizeExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'sizeModifier'?: (_ctk_ast_v1_ArraySizeModifier);
  'indexQualifiers'?: (_ctk_ast_v1_Qualifiers | null);
  '_sizeModifier'?: "sizeModifier";
}

export interface ConstantArrayType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'elementType': (_ctk_ast_v1_QualType__Output | null);
  'size': (_ctk_ast_v1_APIntBits__Output | null);
  'sizeExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'sizeModifier'?: (_ctk_ast_v1_ArraySizeModifier__Output);
  'indexQualifiers': (_ctk_ast_v1_Qualifiers__Output | null);
  '_sizeModifier'?: "sizeModifier";
}
