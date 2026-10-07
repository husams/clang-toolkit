// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { TypeTrait as _ctk_ast_v1_TypeTrait, TypeTrait__Output as _ctk_ast_v1_TypeTrait__Output } from '../../../ctk/ast/v1/TypeTrait.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { APValue as _ctk_ast_v1_APValue, APValue__Output as _ctk_ast_v1_APValue__Output } from '../../../ctk/ast/v1/APValue.js';

export interface TypeTraitExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'trait'?: (_ctk_ast_v1_TypeTrait);
  'queriedTypes'?: (_ctk_ast_v1_QualType)[];
  'traitValue'?: (boolean);
  'resultValue'?: (_ctk_ast_v1_APValue | null);
  'traitName'?: (string);
  '_trait'?: "trait";
  '_traitValue'?: "traitValue";
  '_traitName'?: "traitName";
}

export interface TypeTraitExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'trait'?: (_ctk_ast_v1_TypeTrait__Output);
  'queriedTypes': (_ctk_ast_v1_QualType__Output)[];
  'traitValue'?: (boolean);
  'resultValue': (_ctk_ast_v1_APValue__Output | null);
  'traitName'?: (string);
  '_trait'?: "trait";
  '_traitValue'?: "traitValue";
  '_traitName'?: "traitName";
}
