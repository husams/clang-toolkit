// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { OverloadedOperatorKind as _ctk_ast_v1_OverloadedOperatorKind, OverloadedOperatorKind__Output as _ctk_ast_v1_OverloadedOperatorKind__Output } from '../../../ctk/ast/v1/OverloadedOperatorKind.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { Empty as _ctk_ast_v1_Empty, Empty__Output as _ctk_ast_v1_Empty__Output } from '../../../ctk/ast/v1/Empty.js';

export interface DeclarationName {
  'identifier'?: (string);
  'constructorType'?: (_ctk_ast_v1_QualType | null);
  'destructorType'?: (_ctk_ast_v1_QualType | null);
  'conversionType'?: (_ctk_ast_v1_QualType | null);
  'overloadedOperator'?: (_ctk_ast_v1_OverloadedOperatorKind);
  'literalOperatorSuffix'?: (string);
  'deductionGuideTemplate'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'usingDirective'?: (_ctk_ast_v1_Empty | null);
  'emptyName'?: (_ctk_ast_v1_Empty | null);
  'value'?: "identifier"|"constructorType"|"destructorType"|"conversionType"|"overloadedOperator"|"literalOperatorSuffix"|"deductionGuideTemplate"|"usingDirective"|"emptyName";
}

export interface DeclarationName__Output {
  'identifier'?: (string);
  'constructorType'?: (_ctk_ast_v1_QualType__Output | null);
  'destructorType'?: (_ctk_ast_v1_QualType__Output | null);
  'conversionType'?: (_ctk_ast_v1_QualType__Output | null);
  'overloadedOperator'?: (_ctk_ast_v1_OverloadedOperatorKind__Output);
  'literalOperatorSuffix'?: (string);
  'deductionGuideTemplate'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'usingDirective'?: (_ctk_ast_v1_Empty__Output | null);
  'emptyName'?: (_ctk_ast_v1_Empty__Output | null);
  'value'?: "identifier"|"constructorType"|"destructorType"|"conversionType"|"overloadedOperator"|"literalOperatorSuffix"|"deductionGuideTemplate"|"usingDirective"|"emptyName";
}
