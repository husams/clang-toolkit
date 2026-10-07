// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { APSIntBits as _ctk_ast_v1_APSIntBits, APSIntBits__Output as _ctk_ast_v1_APSIntBits__Output } from '../../../ctk/ast/v1/APSIntBits.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface IntegralTemplateArgument {
  'value'?: (_ctk_ast_v1_APSIntBits | null);
  'type'?: (_ctk_ast_v1_QualType | null);
}

export interface IntegralTemplateArgument__Output {
  'value': (_ctk_ast_v1_APSIntBits__Output | null);
  'type': (_ctk_ast_v1_QualType__Output | null);
}
