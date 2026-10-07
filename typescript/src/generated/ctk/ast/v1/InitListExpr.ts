// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface InitListExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'initializers'?: (_ctk_ast_v1_ExpressionValue)[];
  'syntacticInitializers'?: (_ctk_ast_v1_ExpressionValue)[];
  'arrayFiller'?: (_ctk_ast_v1_ExpressionValue | null);
  'isUnion'?: (boolean);
  'isSemanticForm'?: (boolean);
  '_isUnion'?: "isUnion";
  '_isSemanticForm'?: "isSemanticForm";
}

export interface InitListExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'initializers': (_ctk_ast_v1_ExpressionValue__Output)[];
  'syntacticInitializers': (_ctk_ast_v1_ExpressionValue__Output)[];
  'arrayFiller': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isUnion'?: (boolean);
  'isSemanticForm'?: (boolean);
  '_isUnion'?: "isUnion";
  '_isSemanticForm'?: "isSemanticForm";
}
