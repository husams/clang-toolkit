// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface StaticAssertDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'assertionExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'messageExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'isFailed'?: (boolean);
  '_isFailed'?: "isFailed";
}

export interface StaticAssertDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'assertionExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'messageExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isFailed'?: (boolean);
  '_isFailed'?: "isFailed";
}
