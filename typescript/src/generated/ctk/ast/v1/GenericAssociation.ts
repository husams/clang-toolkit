// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface GenericAssociation {
  'type'?: (_ctk_ast_v1_QualType | null);
  'expression'?: (_ctk_ast_v1_ExpressionValue | null);
  'isDefault'?: (boolean);
  'isSelected'?: (boolean);
  '_isDefault'?: "isDefault";
  '_isSelected'?: "isSelected";
}

export interface GenericAssociation__Output {
  'type': (_ctk_ast_v1_QualType__Output | null);
  'expression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isDefault'?: (boolean);
  'isSelected'?: (boolean);
  '_isDefault'?: "isDefault";
  '_isSelected'?: "isSelected";
}
