// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ArrayTypeTrait as _ctk_ast_v1_ArrayTypeTrait, ArrayTypeTrait__Output as _ctk_ast_v1_ArrayTypeTrait__Output } from '../../../ctk/ast/v1/ArrayTypeTrait.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { Long } from '@grpc/proto-loader';

export interface ArrayTypeTraitExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'trait'?: (_ctk_ast_v1_ArrayTypeTrait);
  'queriedType'?: (_ctk_ast_v1_QualType | null);
  'dimension'?: (number | string | Long);
  '_trait'?: "trait";
  '_dimension'?: "dimension";
}

export interface ArrayTypeTraitExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'trait'?: (_ctk_ast_v1_ArrayTypeTrait__Output);
  'queriedType': (_ctk_ast_v1_QualType__Output | null);
  'dimension'?: (string);
  '_trait'?: "trait";
  '_dimension'?: "dimension";
}
