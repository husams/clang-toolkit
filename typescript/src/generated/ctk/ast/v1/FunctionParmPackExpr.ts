// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface FunctionParmPackExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'parameterPack'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'expansions'?: (_ctk_ast_v1_DeclarationSymbol)[];
}

export interface FunctionParmPackExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'parameterPack': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'expansions': (_ctk_ast_v1_DeclarationSymbol__Output)[];
}
