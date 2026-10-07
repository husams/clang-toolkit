// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { GenericAssociation as _ctk_ast_v1_GenericAssociation, GenericAssociation__Output as _ctk_ast_v1_GenericAssociation__Output } from '../../../ctk/ast/v1/GenericAssociation.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface GenericSelectionExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'controllingExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'resultExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'associations'?: (_ctk_ast_v1_GenericAssociation)[];
  'selectedIndex'?: (number);
  'controllingType'?: (_ctk_ast_v1_QualType | null);
  '_selectedIndex'?: "selectedIndex";
}

export interface GenericSelectionExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'controllingExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'resultExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'associations': (_ctk_ast_v1_GenericAssociation__Output)[];
  'selectedIndex'?: (number);
  'controllingType': (_ctk_ast_v1_QualType__Output | null);
  '_selectedIndex'?: "selectedIndex";
}
