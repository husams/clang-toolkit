// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { Long } from '@grpc/proto-loader';

export interface EmbedExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'fileName'?: (string);
  'startingElementPosition'?: (number);
  'dataElementCount'?: (number | string | Long);
  'dataStringLiteral'?: (_ctk_ast_v1_ExpressionValue | null);
  '_fileName'?: "fileName";
  '_startingElementPosition'?: "startingElementPosition";
  '_dataElementCount'?: "dataElementCount";
}

export interface EmbedExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'fileName'?: (string);
  'startingElementPosition'?: (number);
  'dataElementCount'?: (string);
  'dataStringLiteral': (_ctk_ast_v1_ExpressionValue__Output | null);
  '_fileName'?: "fileName";
  '_startingElementPosition'?: "startingElementPosition";
  '_dataElementCount'?: "dataElementCount";
}
