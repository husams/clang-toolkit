// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ConceptReference as _ctk_ast_v1_ConceptReference, ConceptReference__Output as _ctk_ast_v1_ConceptReference__Output } from '../../../ctk/ast/v1/ConceptReference.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface TypeConstraint {
  'conceptReference'?: (_ctk_ast_v1_ConceptReference | null);
  'immediatelyDeclaredConstraint'?: (_ctk_ast_v1_ExpressionValue | null);
  'argumentPackSubstitutionIndex'?: (number);
  '_argumentPackSubstitutionIndex'?: "argumentPackSubstitutionIndex";
}

export interface TypeConstraint__Output {
  'conceptReference': (_ctk_ast_v1_ConceptReference__Output | null);
  'immediatelyDeclaredConstraint': (_ctk_ast_v1_ExpressionValue__Output | null);
  'argumentPackSubstitutionIndex'?: (number);
  '_argumentPackSubstitutionIndex'?: "argumentPackSubstitutionIndex";
}
