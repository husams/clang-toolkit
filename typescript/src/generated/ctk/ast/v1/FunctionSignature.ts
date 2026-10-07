// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeDescription as _ctk_ast_v1_TypeDescription, TypeDescription__Output as _ctk_ast_v1_TypeDescription__Output } from '../../../ctk/ast/v1/TypeDescription.js';
import type { ParameterValue as _ctk_ast_v1_ParameterValue, ParameterValue__Output as _ctk_ast_v1_ParameterValue__Output } from '../../../ctk/ast/v1/ParameterValue.js';
import type { RefQualifier as _ctk_ast_v1_RefQualifier, RefQualifier__Output as _ctk_ast_v1_RefQualifier__Output } from '../../../ctk/ast/v1/RefQualifier.js';
import type { FunctionExtInfo as _ctk_ast_v1_FunctionExtInfo, FunctionExtInfo__Output as _ctk_ast_v1_FunctionExtInfo__Output } from '../../../ctk/ast/v1/FunctionExtInfo.js';
import type { ExceptionDescription as _ctk_ast_v1_ExceptionDescription, ExceptionDescription__Output as _ctk_ast_v1_ExceptionDescription__Output } from '../../../ctk/ast/v1/ExceptionDescription.js';
import type { TemplateParameterDescription as _ctk_ast_v1_TemplateParameterDescription, TemplateParameterDescription__Output as _ctk_ast_v1_TemplateParameterDescription__Output } from '../../../ctk/ast/v1/TemplateParameterDescription.js';
import type { ConstraintDescription as _ctk_ast_v1_ConstraintDescription, ConstraintDescription__Output as _ctk_ast_v1_ConstraintDescription__Output } from '../../../ctk/ast/v1/ConstraintDescription.js';

export interface FunctionSignature {
  'returnType'?: (_ctk_ast_v1_TypeDescription | null);
  'parameters'?: (_ctk_ast_v1_ParameterValue)[];
  'isVariadic'?: (boolean);
  'isConst'?: (boolean);
  'isVolatile'?: (boolean);
  'refQualifier'?: (_ctk_ast_v1_RefQualifier);
  'isStatic'?: (boolean);
  'callingConvention'?: (_ctk_ast_v1_FunctionExtInfo | null);
  'exceptionSpecification'?: (_ctk_ast_v1_ExceptionDescription | null);
  'templateParameters'?: (_ctk_ast_v1_TemplateParameterDescription)[];
  'associatedConstraints'?: (_ctk_ast_v1_ConstraintDescription)[];
  '_isVariadic'?: "isVariadic";
  '_isConst'?: "isConst";
  '_isVolatile'?: "isVolatile";
  '_refQualifier'?: "refQualifier";
  '_isStatic'?: "isStatic";
}

export interface FunctionSignature__Output {
  'returnType': (_ctk_ast_v1_TypeDescription__Output | null);
  'parameters': (_ctk_ast_v1_ParameterValue__Output)[];
  'isVariadic'?: (boolean);
  'isConst'?: (boolean);
  'isVolatile'?: (boolean);
  'refQualifier'?: (_ctk_ast_v1_RefQualifier__Output);
  'isStatic'?: (boolean);
  'callingConvention': (_ctk_ast_v1_FunctionExtInfo__Output | null);
  'exceptionSpecification': (_ctk_ast_v1_ExceptionDescription__Output | null);
  'templateParameters': (_ctk_ast_v1_TemplateParameterDescription__Output)[];
  'associatedConstraints': (_ctk_ast_v1_ConstraintDescription__Output)[];
  '_isVariadic'?: "isVariadic";
  '_isConst'?: "isConst";
  '_isVolatile'?: "isVolatile";
  '_refQualifier'?: "refQualifier";
  '_isStatic'?: "isStatic";
}
