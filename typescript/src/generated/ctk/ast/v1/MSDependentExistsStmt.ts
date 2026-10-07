// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface MSDependentExistsStmt {
  'substatement'?: (_ctk_ast_v1_StatementValue | null);
  'identifier'?: (string);
  'isIfExists'?: (boolean);
  '_identifier'?: "identifier";
  '_isIfExists'?: "isIfExists";
}

export interface MSDependentExistsStmt__Output {
  'substatement': (_ctk_ast_v1_StatementValue__Output | null);
  'identifier'?: (string);
  'isIfExists'?: (boolean);
  '_identifier'?: "identifier";
  '_isIfExists'?: "isIfExists";
}
