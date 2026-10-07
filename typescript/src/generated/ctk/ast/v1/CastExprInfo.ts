// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { CastKind as _ctk_ast_v1_CastKind, CastKind__Output as _ctk_ast_v1_CastKind__Output } from '../../../ctk/ast/v1/CastKind.js';
import type { CXXBaseSpecifier as _ctk_ast_v1_CXXBaseSpecifier, CXXBaseSpecifier__Output as _ctk_ast_v1_CXXBaseSpecifier__Output } from '../../../ctk/ast/v1/CXXBaseSpecifier.js';

export interface CastExprInfo {
  'expression'?: (_ctk_ast_v1_ExprInfo | null);
  'operand'?: (_ctk_ast_v1_ExpressionValue | null);
  'kind'?: (_ctk_ast_v1_CastKind);
  'basePath'?: (_ctk_ast_v1_CXXBaseSpecifier)[];
  '_kind'?: "kind";
}

export interface CastExprInfo__Output {
  'expression': (_ctk_ast_v1_ExprInfo__Output | null);
  'operand': (_ctk_ast_v1_ExpressionValue__Output | null);
  'kind'?: (_ctk_ast_v1_CastKind__Output);
  'basePath': (_ctk_ast_v1_CXXBaseSpecifier__Output)[];
  '_kind'?: "kind";
}
