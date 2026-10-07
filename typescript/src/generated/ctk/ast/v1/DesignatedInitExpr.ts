// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { Designator as _ctk_ast_v1_Designator, Designator__Output as _ctk_ast_v1_Designator__Output } from '../../../ctk/ast/v1/Designator.js';

export interface DesignatedInitExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'initializer'?: (_ctk_ast_v1_ExpressionValue | null);
  'designators'?: (_ctk_ast_v1_Designator)[];
}

export interface DesignatedInitExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'initializer': (_ctk_ast_v1_ExpressionValue__Output | null);
  'designators': (_ctk_ast_v1_Designator__Output)[];
}
