// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ValueDeclInfo as _ctk_ast_v1_ValueDeclInfo, ValueDeclInfo__Output as _ctk_ast_v1_ValueDeclInfo__Output } from '../../../ctk/ast/v1/ValueDeclInfo.js';
import type { APValue as _ctk_ast_v1_APValue, APValue__Output as _ctk_ast_v1_APValue__Output } from '../../../ctk/ast/v1/APValue.js';

export interface UnnamedGlobalConstantDecl {
  'value'?: (_ctk_ast_v1_ValueDeclInfo | null);
  'valueAsConstant'?: (_ctk_ast_v1_APValue | null);
}

export interface UnnamedGlobalConstantDecl__Output {
  'value': (_ctk_ast_v1_ValueDeclInfo__Output | null);
  'valueAsConstant': (_ctk_ast_v1_APValue__Output | null);
}
