// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/cfg_destructor.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { CXXBaseSpecifier as _ctk_ast_v1_CXXBaseSpecifier, CXXBaseSpecifier__Output as _ctk_ast_v1_CXXBaseSpecifier__Output } from '../../../ctk/ast/v1/CXXBaseSpecifier.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';

export interface CfgDestructor {
  'destructor'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'isNoReturn'?: (boolean);
  'variable'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'record'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'field'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'base'?: (_ctk_ast_v1_CXXBaseSpecifier | null);
  'trigger'?: (_ctk_ast_v1_StatementValue | null);
}

export interface CfgDestructor__Output {
  'destructor': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'isNoReturn': (boolean);
  'variable': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'record': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'field': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'base': (_ctk_ast_v1_CXXBaseSpecifier__Output | null);
  'trigger': (_ctk_ast_v1_StatementValue__Output | null);
}
