// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { TypeOfKind as _ctk_ast_v1_TypeOfKind, TypeOfKind__Output as _ctk_ast_v1_TypeOfKind__Output } from '../../../ctk/ast/v1/TypeOfKind.js';

export interface TypeOfExprType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'underlyingExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'kind'?: (_ctk_ast_v1_TypeOfKind);
  '_kind'?: "kind";
}

export interface TypeOfExprType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'underlyingExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'kind'?: (_ctk_ast_v1_TypeOfKind__Output);
  '_kind'?: "kind";
}
