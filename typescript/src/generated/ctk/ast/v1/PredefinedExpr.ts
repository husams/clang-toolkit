// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { PredefinedIdentKind as _ctk_ast_v1_PredefinedIdentKind, PredefinedIdentKind__Output as _ctk_ast_v1_PredefinedIdentKind__Output } from '../../../ctk/ast/v1/PredefinedIdentKind.js';

export interface PredefinedExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'identifierKind'?: (_ctk_ast_v1_PredefinedIdentKind);
  'literalBytes'?: (Buffer | Uint8Array | string);
  '_identifierKind'?: "identifierKind";
  '_literalBytes'?: "literalBytes";
}

export interface PredefinedExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'identifierKind'?: (_ctk_ast_v1_PredefinedIdentKind__Output);
  'literalBytes'?: (Buffer);
  '_identifierKind'?: "identifierKind";
  '_literalBytes'?: "literalBytes";
}
