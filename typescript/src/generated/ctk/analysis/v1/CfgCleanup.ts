// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_cleanup.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface CfgCleanup {
  'variable'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'function'?: (_ctk_ast_v1_DeclarationSymbol | null);
}

export interface CfgCleanup__Output {
  'variable': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'function': (_ctk_ast_v1_DeclarationSymbol__Output | null);
}
