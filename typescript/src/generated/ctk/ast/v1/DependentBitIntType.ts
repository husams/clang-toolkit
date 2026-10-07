// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface DependentBitIntType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'bitWidthExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'isUnsigned'?: (boolean);
  '_isUnsigned'?: "isUnsigned";
}

export interface DependentBitIntType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'bitWidthExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isUnsigned'?: (boolean);
  '_isUnsigned'?: "isUnsigned";
}
