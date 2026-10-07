// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { AutoKeyword as _ctk_ast_v1_AutoKeyword, AutoKeyword__Output as _ctk_ast_v1_AutoKeyword__Output } from '../../../ctk/ast/v1/AutoKeyword.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { TemplateArgument as _ctk_ast_v1_TemplateArgument, TemplateArgument__Output as _ctk_ast_v1_TemplateArgument__Output } from '../../../ctk/ast/v1/TemplateArgument.js';

export interface AutoType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'deducedType'?: (_ctk_ast_v1_QualType | null);
  'keyword'?: (_ctk_ast_v1_AutoKeyword);
  'isConstrained'?: (boolean);
  'typeConstraintConcept'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'typeConstraintArguments'?: (_ctk_ast_v1_TemplateArgument)[];
  '_keyword'?: "keyword";
  '_isConstrained'?: "isConstrained";
}

export interface AutoType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'deducedType': (_ctk_ast_v1_QualType__Output | null);
  'keyword'?: (_ctk_ast_v1_AutoKeyword__Output);
  'isConstrained'?: (boolean);
  'typeConstraintConcept': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'typeConstraintArguments': (_ctk_ast_v1_TemplateArgument__Output)[];
  '_keyword'?: "keyword";
  '_isConstrained'?: "isConstrained";
}
