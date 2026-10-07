// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface CXXInheritedCtorInitExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'constructor'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'constructingConstructor'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'isConstructedInClass'?: (boolean);
  '_isConstructedInClass'?: "isConstructedInClass";
}

export interface CXXInheritedCtorInitExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'constructor': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'constructingConstructor': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'isConstructedInClass'?: (boolean);
  '_isConstructedInClass'?: "isConstructedInClass";
}
