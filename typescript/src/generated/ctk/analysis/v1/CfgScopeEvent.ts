// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_scope_event.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface CfgScopeEvent {
  'variable'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'trigger'?: (_ctk_ast_v1_StatementValue | null);
}

export interface CfgScopeEvent__Output {
  'variable': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'trigger': (_ctk_ast_v1_StatementValue__Output | null);
}
