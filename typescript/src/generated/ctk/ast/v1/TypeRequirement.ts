// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { RequirementInfo as _ctk_ast_v1_RequirementInfo, RequirementInfo__Output as _ctk_ast_v1_RequirementInfo__Output } from '../../../ctk/ast/v1/RequirementInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { SubstitutionDiagnostic as _ctk_ast_v1_SubstitutionDiagnostic, SubstitutionDiagnostic__Output as _ctk_ast_v1_SubstitutionDiagnostic__Output } from '../../../ctk/ast/v1/SubstitutionDiagnostic.js';

export interface TypeRequirement {
  'requirement'?: (_ctk_ast_v1_RequirementInfo | null);
  'requiredType'?: (_ctk_ast_v1_QualType | null);
  'substitutionError'?: (_ctk_ast_v1_SubstitutionDiagnostic | null);
  'result'?: "requiredType"|"substitutionError";
}

export interface TypeRequirement__Output {
  'requirement': (_ctk_ast_v1_RequirementInfo__Output | null);
  'requiredType'?: (_ctk_ast_v1_QualType__Output | null);
  'substitutionError'?: (_ctk_ast_v1_SubstitutionDiagnostic__Output | null);
  'result'?: "requiredType"|"substitutionError";
}
