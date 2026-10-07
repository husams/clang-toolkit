// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExceptionSpecification as _ctk_ast_v1_ExceptionSpecification, ExceptionSpecification__Output as _ctk_ast_v1_ExceptionSpecification__Output } from '../../../ctk/ast/v1/ExceptionSpecification.js';
import type { TypeDescription as _ctk_ast_v1_TypeDescription, TypeDescription__Output as _ctk_ast_v1_TypeDescription__Output } from '../../../ctk/ast/v1/TypeDescription.js';
import type { ConstraintDescription as _ctk_ast_v1_ConstraintDescription, ConstraintDescription__Output as _ctk_ast_v1_ConstraintDescription__Output } from '../../../ctk/ast/v1/ConstraintDescription.js';

export interface ExceptionDescription {
  'kind'?: (_ctk_ast_v1_ExceptionSpecification);
  'exceptionTypes'?: (_ctk_ast_v1_TypeDescription)[];
  'isNoexcept'?: (boolean);
  'dependentCondition'?: (_ctk_ast_v1_ConstraintDescription | null);
  '_kind'?: "kind";
  '_isNoexcept'?: "isNoexcept";
}

export interface ExceptionDescription__Output {
  'kind'?: (_ctk_ast_v1_ExceptionSpecification__Output);
  'exceptionTypes': (_ctk_ast_v1_TypeDescription__Output)[];
  'isNoexcept'?: (boolean);
  'dependentCondition': (_ctk_ast_v1_ConstraintDescription__Output | null);
  '_kind'?: "kind";
  '_isNoexcept'?: "isNoexcept";
}
