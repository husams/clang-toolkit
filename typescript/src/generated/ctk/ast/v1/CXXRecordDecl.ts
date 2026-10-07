// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { RecordDeclInfo as _ctk_ast_v1_RecordDeclInfo, RecordDeclInfo__Output as _ctk_ast_v1_RecordDeclInfo__Output } from '../../../ctk/ast/v1/RecordDeclInfo.js';
import type { CXXBaseSpecifier as _ctk_ast_v1_CXXBaseSpecifier, CXXBaseSpecifier__Output as _ctk_ast_v1_CXXBaseSpecifier__Output } from '../../../ctk/ast/v1/CXXBaseSpecifier.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';

export interface CXXRecordDecl {
  'record'?: (_ctk_ast_v1_RecordDeclInfo | null);
  'definitionBases'?: (_ctk_ast_v1_CXXBaseSpecifier)[];
  'friends'?: (_ctk_ast_v1_DeclarationValue)[];
  'isLambda'?: (boolean);
  'isStructural'?: (boolean);
  '_isLambda'?: "isLambda";
  '_isStructural'?: "isStructural";
}

export interface CXXRecordDecl__Output {
  'record': (_ctk_ast_v1_RecordDeclInfo__Output | null);
  'definitionBases': (_ctk_ast_v1_CXXBaseSpecifier__Output)[];
  'friends': (_ctk_ast_v1_DeclarationValue__Output)[];
  'isLambda'?: (boolean);
  'isStructural'?: (boolean);
  '_isLambda'?: "isLambda";
  '_isStructural'?: "isStructural";
}
