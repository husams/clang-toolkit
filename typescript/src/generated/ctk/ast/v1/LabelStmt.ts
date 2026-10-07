// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface LabelStmt {
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'substatement'?: (_ctk_ast_v1_StatementValue | null);
  'isGnuAsmLabel'?: (boolean);
  '_isGnuAsmLabel'?: "isGnuAsmLabel";
}

export interface LabelStmt__Output {
  'declaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'substatement': (_ctk_ast_v1_StatementValue__Output | null);
  'isGnuAsmLabel'?: (boolean);
  '_isGnuAsmLabel'?: "isGnuAsmLabel";
}
