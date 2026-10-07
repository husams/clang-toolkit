// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { Empty as _ctk_ast_v1_Empty, Empty__Output as _ctk_ast_v1_Empty__Output } from '../../../ctk/ast/v1/Empty.js';
import type { TemplateParameterList as _ctk_ast_v1_TemplateParameterList, TemplateParameterList__Output as _ctk_ast_v1_TemplateParameterList__Output } from '../../../ctk/ast/v1/TemplateParameterList.js';
import type { SubstitutionDiagnostic as _ctk_ast_v1_SubstitutionDiagnostic, SubstitutionDiagnostic__Output as _ctk_ast_v1_SubstitutionDiagnostic__Output } from '../../../ctk/ast/v1/SubstitutionDiagnostic.js';

export interface ReturnTypeRequirement {
  'unconstrained'?: (_ctk_ast_v1_Empty | null);
  'constraintParameters'?: (_ctk_ast_v1_TemplateParameterList | null);
  'substitutionError'?: (_ctk_ast_v1_SubstitutionDiagnostic | null);
  'isDependent'?: (boolean);
  'containsUnexpandedParameterPack'?: (boolean);
  '_isDependent'?: "isDependent";
  'value'?: "unconstrained"|"constraintParameters"|"substitutionError";
  '_containsUnexpandedParameterPack'?: "containsUnexpandedParameterPack";
}

export interface ReturnTypeRequirement__Output {
  'unconstrained'?: (_ctk_ast_v1_Empty__Output | null);
  'constraintParameters'?: (_ctk_ast_v1_TemplateParameterList__Output | null);
  'substitutionError'?: (_ctk_ast_v1_SubstitutionDiagnostic__Output | null);
  'isDependent'?: (boolean);
  'containsUnexpandedParameterPack'?: (boolean);
  '_isDependent'?: "isDependent";
  'value'?: "unconstrained"|"constraintParameters"|"substitutionError";
  '_containsUnexpandedParameterPack'?: "containsUnexpandedParameterPack";
}
