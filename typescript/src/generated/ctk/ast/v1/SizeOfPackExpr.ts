// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { Long } from '@grpc/proto-loader';

export interface SizeOfPackExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'packDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'packSize'?: (number | string | Long);
  '_packSize'?: "packSize";
}

export interface SizeOfPackExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'packDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'packSize'?: (string);
  '_packSize'?: "packSize";
}
