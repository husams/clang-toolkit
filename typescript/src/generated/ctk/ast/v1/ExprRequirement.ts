// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { RequirementInfo as _ctk_ast_v1_RequirementInfo, RequirementInfo__Output as _ctk_ast_v1_RequirementInfo__Output } from '../../../ctk/ast/v1/RequirementInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { SubstitutionDiagnostic as _ctk_ast_v1_SubstitutionDiagnostic, SubstitutionDiagnostic__Output as _ctk_ast_v1_SubstitutionDiagnostic__Output } from '../../../ctk/ast/v1/SubstitutionDiagnostic.js';
import type { ReturnTypeRequirement as _ctk_ast_v1_ReturnTypeRequirement, ReturnTypeRequirement__Output as _ctk_ast_v1_ReturnTypeRequirement__Output } from '../../../ctk/ast/v1/ReturnTypeRequirement.js';
import type { ExprRequirementSatisfactionStatus as _ctk_ast_v1_ExprRequirementSatisfactionStatus, ExprRequirementSatisfactionStatus__Output as _ctk_ast_v1_ExprRequirementSatisfactionStatus__Output } from '../../../ctk/ast/v1/ExprRequirementSatisfactionStatus.js';

export interface ExprRequirement {
  'requirement'?: (_ctk_ast_v1_RequirementInfo | null);
  'expression'?: (_ctk_ast_v1_ExpressionValue | null);
  'substitutionError'?: (_ctk_ast_v1_SubstitutionDiagnostic | null);
  'isSimple'?: (boolean);
  'returnType'?: (_ctk_ast_v1_ReturnTypeRequirement | null);
  'satisfactionStatus'?: (_ctk_ast_v1_ExprRequirementSatisfactionStatus);
  'substitutedReturnTypeConstraint'?: (_ctk_ast_v1_ExpressionValue | null);
  '_isSimple'?: "isSimple";
  '_satisfactionStatus'?: "satisfactionStatus";
  'result'?: "expression"|"substitutionError";
}

export interface ExprRequirement__Output {
  'requirement': (_ctk_ast_v1_RequirementInfo__Output | null);
  'expression'?: (_ctk_ast_v1_ExpressionValue__Output | null);
  'substitutionError'?: (_ctk_ast_v1_SubstitutionDiagnostic__Output | null);
  'isSimple'?: (boolean);
  'returnType': (_ctk_ast_v1_ReturnTypeRequirement__Output | null);
  'satisfactionStatus'?: (_ctk_ast_v1_ExprRequirementSatisfactionStatus__Output);
  'substitutedReturnTypeConstraint': (_ctk_ast_v1_ExpressionValue__Output | null);
  '_isSimple'?: "isSimple";
  '_satisfactionStatus'?: "satisfactionStatus";
  'result'?: "expression"|"substitutionError";
}
