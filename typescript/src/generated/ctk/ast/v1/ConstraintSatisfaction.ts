// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ConstraintDetail as _ctk_ast_v1_ConstraintDetail, ConstraintDetail__Output as _ctk_ast_v1_ConstraintDetail__Output } from '../../../ctk/ast/v1/ConstraintDetail.js';

export interface ConstraintSatisfaction {
  'isSatisfied'?: (boolean);
  'containsErrors'?: (boolean);
  'details'?: (_ctk_ast_v1_ConstraintDetail)[];
  '_isSatisfied'?: "isSatisfied";
  '_containsErrors'?: "containsErrors";
}

export interface ConstraintSatisfaction__Output {
  'isSatisfied'?: (boolean);
  'containsErrors'?: (boolean);
  'details': (_ctk_ast_v1_ConstraintDetail__Output)[];
  '_isSatisfied'?: "isSatisfied";
  '_containsErrors'?: "containsErrors";
}
