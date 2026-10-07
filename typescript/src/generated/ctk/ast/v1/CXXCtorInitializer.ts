// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CXXCtorInitializer {
  'baseType'?: (_ctk_ast_v1_QualType | null);
  'member'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'indirectMember'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'delegatingType'?: (_ctk_ast_v1_QualType | null);
  'initializer'?: (_ctk_ast_v1_ExpressionValue | null);
  'isVirtualBase'?: (boolean);
  'isPackExpansion'?: (boolean);
  '_isVirtualBase'?: "isVirtualBase";
  '_isPackExpansion'?: "isPackExpansion";
  'target'?: "baseType"|"member"|"indirectMember"|"delegatingType";
}

export interface CXXCtorInitializer__Output {
  'baseType'?: (_ctk_ast_v1_QualType__Output | null);
  'member'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'indirectMember'?: (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'delegatingType'?: (_ctk_ast_v1_QualType__Output | null);
  'initializer': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isVirtualBase'?: (boolean);
  'isPackExpansion'?: (boolean);
  '_isVirtualBase'?: "isVirtualBase";
  '_isPackExpansion'?: "isPackExpansion";
  'target'?: "baseType"|"member"|"indirectMember"|"delegatingType";
}
