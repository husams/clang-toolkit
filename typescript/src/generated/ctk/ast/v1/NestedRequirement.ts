// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { RequirementInfo as _ctk_ast_v1_RequirementInfo, RequirementInfo__Output as _ctk_ast_v1_RequirementInfo__Output } from '../../../ctk/ast/v1/RequirementInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { ConstraintSatisfaction as _ctk_ast_v1_ConstraintSatisfaction, ConstraintSatisfaction__Output as _ctk_ast_v1_ConstraintSatisfaction__Output } from '../../../ctk/ast/v1/ConstraintSatisfaction.js';

export interface NestedRequirement {
  'requirement'?: (_ctk_ast_v1_RequirementInfo | null);
  'constraintExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'satisfaction'?: (_ctk_ast_v1_ConstraintSatisfaction | null);
  'hasInvalidConstraint'?: (boolean);
  'invalidConstraintEntity'?: (string);
  '_hasInvalidConstraint'?: "hasInvalidConstraint";
  '_invalidConstraintEntity'?: "invalidConstraintEntity";
}

export interface NestedRequirement__Output {
  'requirement': (_ctk_ast_v1_RequirementInfo__Output | null);
  'constraintExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'satisfaction': (_ctk_ast_v1_ConstraintSatisfaction__Output | null);
  'hasInvalidConstraint'?: (boolean);
  'invalidConstraintEntity'?: (string);
  '_hasInvalidConstraint'?: "hasInvalidConstraint";
  '_invalidConstraintEntity'?: "invalidConstraintEntity";
}
