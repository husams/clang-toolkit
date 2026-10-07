// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { CleanupValue as _ctk_ast_v1_CleanupValue, CleanupValue__Output as _ctk_ast_v1_CleanupValue__Output } from '../../../ctk/ast/v1/CleanupValue.js';

export interface ExprWithCleanups {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'subexpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'cleanups'?: (_ctk_ast_v1_CleanupValue)[];
}

export interface ExprWithCleanups__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'subexpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'cleanups': (_ctk_ast_v1_CleanupValue__Output)[];
}
