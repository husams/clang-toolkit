// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { NamedDeclInfo as _ctk_ast_v1_NamedDeclInfo, NamedDeclInfo__Output as _ctk_ast_v1_NamedDeclInfo__Output } from '../../../ctk/ast/v1/NamedDeclInfo.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface LabelDecl {
  'named'?: (_ctk_ast_v1_NamedDeclInfo | null);
  'statement'?: (_ctk_ast_v1_StatementValue | null);
  'isGnuLocal'?: (boolean);
  '_isGnuLocal'?: "isGnuLocal";
}

export interface LabelDecl__Output {
  'named': (_ctk_ast_v1_NamedDeclInfo__Output | null);
  'statement': (_ctk_ast_v1_StatementValue__Output | null);
  'isGnuLocal'?: (boolean);
  '_isGnuLocal'?: "isGnuLocal";
}
