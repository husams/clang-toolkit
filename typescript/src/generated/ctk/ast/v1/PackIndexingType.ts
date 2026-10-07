// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface PackIndexingType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'patternType'?: (_ctk_ast_v1_QualType | null);
  'indexExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'selectedIndex'?: (number);
  'selectedType'?: (_ctk_ast_v1_QualType | null);
  '_selectedIndex'?: "selectedIndex";
  '_selectedType'?: "selectedType";
}

export interface PackIndexingType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'patternType': (_ctk_ast_v1_QualType__Output | null);
  'indexExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'selectedIndex'?: (number);
  'selectedType'?: (_ctk_ast_v1_QualType__Output | null);
  '_selectedIndex'?: "selectedIndex";
  '_selectedType'?: "selectedType";
}
