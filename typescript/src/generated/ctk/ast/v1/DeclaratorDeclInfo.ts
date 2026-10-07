// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ValueDeclInfo as _ctk_ast_v1_ValueDeclInfo, ValueDeclInfo__Output as _ctk_ast_v1_ValueDeclInfo__Output } from '../../../ctk/ast/v1/ValueDeclInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface DeclaratorDeclInfo {
  'value'?: (_ctk_ast_v1_ValueDeclInfo | null);
  'declaredType'?: (_ctk_ast_v1_QualType | null);
}

export interface DeclaratorDeclInfo__Output {
  'value': (_ctk_ast_v1_ValueDeclInfo__Output | null);
  'declaredType': (_ctk_ast_v1_QualType__Output | null);
}
