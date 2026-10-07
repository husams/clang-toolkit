// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { SourceLocExprKind as _ctk_ast_v1_SourceLocExprKind, SourceLocExprKind__Output as _ctk_ast_v1_SourceLocExprKind__Output } from '../../../ctk/ast/v1/SourceLocExprKind.js';

export interface SourceLocExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'parentContext'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'kind'?: (_ctk_ast_v1_SourceLocExprKind);
  'builtinName'?: (string);
  '_kind'?: "kind";
  '_builtinName'?: "builtinName";
}

export interface SourceLocExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'parentContext': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'kind'?: (_ctk_ast_v1_SourceLocExprKind__Output);
  'builtinName'?: (string);
  '_kind'?: "kind";
  '_builtinName'?: "builtinName";
}
