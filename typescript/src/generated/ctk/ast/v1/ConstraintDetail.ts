// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { SubstitutionDiagnostic as _ctk_ast_v1_SubstitutionDiagnostic, SubstitutionDiagnostic__Output as _ctk_ast_v1_SubstitutionDiagnostic__Output } from '../../../ctk/ast/v1/SubstitutionDiagnostic.js';
import type { ConceptReference as _ctk_ast_v1_ConceptReference, ConceptReference__Output as _ctk_ast_v1_ConceptReference__Output } from '../../../ctk/ast/v1/ConceptReference.js';

export interface ConstraintDetail {
  'substitutedConstraint'?: (_ctk_ast_v1_ExpressionValue | null);
  'diagnostic'?: (_ctk_ast_v1_SubstitutionDiagnostic | null);
  'conceptReference'?: (_ctk_ast_v1_ConceptReference | null);
  'detail'?: "substitutedConstraint"|"diagnostic"|"conceptReference";
}

export interface ConstraintDetail__Output {
  'substitutedConstraint'?: (_ctk_ast_v1_ExpressionValue__Output | null);
  'diagnostic'?: (_ctk_ast_v1_SubstitutionDiagnostic__Output | null);
  'conceptReference'?: (_ctk_ast_v1_ConceptReference__Output | null);
  'detail'?: "substitutedConstraint"|"diagnostic"|"conceptReference";
}
