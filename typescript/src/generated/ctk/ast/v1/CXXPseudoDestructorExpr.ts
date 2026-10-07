// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { NestedNameSpecifier as _ctk_ast_v1_NestedNameSpecifier, NestedNameSpecifier__Output as _ctk_ast_v1_NestedNameSpecifier__Output } from '../../../ctk/ast/v1/NestedNameSpecifier.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface CXXPseudoDestructorExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'base'?: (_ctk_ast_v1_ExpressionValue | null);
  'qualifier'?: (_ctk_ast_v1_NestedNameSpecifier | null);
  'destroyedType'?: (_ctk_ast_v1_QualType | null);
  'isArrow'?: (boolean);
  '_isArrow'?: "isArrow";
}

export interface CXXPseudoDestructorExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'base': (_ctk_ast_v1_ExpressionValue__Output | null);
  'qualifier': (_ctk_ast_v1_NestedNameSpecifier__Output | null);
  'destroyedType': (_ctk_ast_v1_QualType__Output | null);
  'isArrow'?: (boolean);
  '_isArrow'?: "isArrow";
}
