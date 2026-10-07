// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExceptionSpecification as _ctk_ast_v1_ExceptionSpecification, ExceptionSpecification__Output as _ctk_ast_v1_ExceptionSpecification__Output } from '../../../ctk/ast/v1/ExceptionSpecification.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { RefQualifier as _ctk_ast_v1_RefQualifier, RefQualifier__Output as _ctk_ast_v1_RefQualifier__Output } from '../../../ctk/ast/v1/RefQualifier.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { Qualifiers as _ctk_ast_v1_Qualifiers, Qualifiers__Output as _ctk_ast_v1_Qualifiers__Output } from '../../../ctk/ast/v1/Qualifiers.js';

export interface FunctionProtoExtInfo {
  'exceptionSpecification'?: (_ctk_ast_v1_ExceptionSpecification);
  'exceptionTypes'?: (_ctk_ast_v1_QualType)[];
  'refQualifier'?: (_ctk_ast_v1_RefQualifier);
  'noexceptExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'exceptionSpecificationDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'exceptionSpecificationTemplate'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'typeQualifiers'?: (_ctk_ast_v1_Qualifiers | null);
  'isCfiUncheckedCallee'?: (boolean);
  '_exceptionSpecification'?: "exceptionSpecification";
  '_refQualifier'?: "refQualifier";
  '_isCfiUncheckedCallee'?: "isCfiUncheckedCallee";
}

export interface FunctionProtoExtInfo__Output {
  'exceptionSpecification'?: (_ctk_ast_v1_ExceptionSpecification__Output);
  'exceptionTypes': (_ctk_ast_v1_QualType__Output)[];
  'refQualifier'?: (_ctk_ast_v1_RefQualifier__Output);
  'noexceptExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'exceptionSpecificationDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'exceptionSpecificationTemplate': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'typeQualifiers': (_ctk_ast_v1_Qualifiers__Output | null);
  'isCfiUncheckedCallee'?: (boolean);
  '_exceptionSpecification'?: "exceptionSpecification";
  '_refQualifier'?: "refQualifier";
  '_isCfiUncheckedCallee'?: "isCfiUncheckedCallee";
}
