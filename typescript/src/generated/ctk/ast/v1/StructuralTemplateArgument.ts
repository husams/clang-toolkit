// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { APValue as _ctk_ast_v1_APValue, APValue__Output as _ctk_ast_v1_APValue__Output } from '../../../ctk/ast/v1/APValue.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface StructuralTemplateArgument {
  'value'?: (_ctk_ast_v1_APValue | null);
  'type'?: (_ctk_ast_v1_QualType | null);
}

export interface StructuralTemplateArgument__Output {
  'value': (_ctk_ast_v1_APValue__Output | null);
  'type': (_ctk_ast_v1_QualType__Output | null);
}
