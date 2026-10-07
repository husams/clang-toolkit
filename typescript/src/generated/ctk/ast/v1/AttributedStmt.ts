// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { AttributeValue as _ctk_ast_v1_AttributeValue, AttributeValue__Output as _ctk_ast_v1_AttributeValue__Output } from '../../../ctk/ast/v1/AttributeValue.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface AttributedStmt {
  'attributes'?: (_ctk_ast_v1_AttributeValue)[];
  'substatement'?: (_ctk_ast_v1_StatementValue | null);
}

export interface AttributedStmt__Output {
  'attributes': (_ctk_ast_v1_AttributeValue__Output)[];
  'substatement': (_ctk_ast_v1_StatementValue__Output | null);
}
