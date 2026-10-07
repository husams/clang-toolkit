// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface ConstantMatrixType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'elementType'?: (_ctk_ast_v1_QualType | null);
  'rowCount'?: (number);
  'columnCount'?: (number);
  '_rowCount'?: "rowCount";
  '_columnCount'?: "columnCount";
}

export interface ConstantMatrixType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'elementType': (_ctk_ast_v1_QualType__Output | null);
  'rowCount'?: (number);
  'columnCount'?: (number);
  '_rowCount'?: "rowCount";
  '_columnCount'?: "columnCount";
}
