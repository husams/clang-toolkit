// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface DecltypeType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'underlyingExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'underlyingType'?: (_ctk_ast_v1_QualType | null);
}

export interface DecltypeType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'underlyingExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'underlyingType': (_ctk_ast_v1_QualType__Output | null);
}
