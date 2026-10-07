// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ValueDeclInfo as _ctk_ast_v1_ValueDeclInfo, ValueDeclInfo__Output as _ctk_ast_v1_ValueDeclInfo__Output } from '../../../ctk/ast/v1/ValueDeclInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { APSIntBits as _ctk_ast_v1_APSIntBits, APSIntBits__Output as _ctk_ast_v1_APSIntBits__Output } from '../../../ctk/ast/v1/APSIntBits.js';

export interface EnumConstantDecl {
  'value'?: (_ctk_ast_v1_ValueDeclInfo | null);
  'initializer'?: (_ctk_ast_v1_ExpressionValue | null);
  'evaluatedValue'?: (_ctk_ast_v1_APSIntBits | null);
}

export interface EnumConstantDecl__Output {
  'value': (_ctk_ast_v1_ValueDeclInfo__Output | null);
  'initializer': (_ctk_ast_v1_ExpressionValue__Output | null);
  'evaluatedValue': (_ctk_ast_v1_APSIntBits__Output | null);
}
