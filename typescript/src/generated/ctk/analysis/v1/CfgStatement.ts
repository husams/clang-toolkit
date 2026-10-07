// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_statement.proto

import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';
import type { CfgConstructionContext as _ctk_analysis_v1_CfgConstructionContext, CfgConstructionContext__Output as _ctk_analysis_v1_CfgConstructionContext__Output } from '../../../ctk/analysis/v1/CfgConstructionContext.js';

export interface CfgStatement {
  'statement'?: (_ctk_ast_v1_StatementValue | null);
  'constructionContext'?: (_ctk_analysis_v1_CfgConstructionContext | null);
}

export interface CfgStatement__Output {
  'statement': (_ctk_ast_v1_StatementValue__Output | null);
  'constructionContext': (_ctk_analysis_v1_CfgConstructionContext__Output | null);
}
