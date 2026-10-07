// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface CXXCatchStmt {
  'exceptionDeclaration'?: (_ctk_ast_v1_DeclarationValue | null);
  'handlerBlock'?: (_ctk_ast_v1_StatementValue | null);
  'isCatchAll'?: (boolean);
  '_isCatchAll'?: "isCatchAll";
}

export interface CXXCatchStmt__Output {
  'exceptionDeclaration': (_ctk_ast_v1_DeclarationValue__Output | null);
  'handlerBlock': (_ctk_ast_v1_StatementValue__Output | null);
  'isCatchAll'?: (boolean);
  '_isCatchAll'?: "isCatchAll";
}
