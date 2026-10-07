// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { LambdaCapture as _ctk_ast_v1_LambdaCapture, LambdaCapture__Output as _ctk_ast_v1_LambdaCapture__Output } from '../../../ctk/ast/v1/LambdaCapture.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface LambdaExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'closureClass'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'captures'?: (_ctk_ast_v1_LambdaCapture)[];
  'captureInitializers'?: (_ctk_ast_v1_ExpressionValue)[];
  'callOperator'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'isGenericLambda'?: (boolean);
  'isMutable'?: (boolean);
  '_isGenericLambda'?: "isGenericLambda";
  '_isMutable'?: "isMutable";
}

export interface LambdaExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'closureClass': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'captures': (_ctk_ast_v1_LambdaCapture__Output)[];
  'captureInitializers': (_ctk_ast_v1_ExpressionValue__Output)[];
  'callOperator': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'isGenericLambda'?: (boolean);
  'isMutable'?: (boolean);
  '_isGenericLambda'?: "isGenericLambda";
  '_isMutable'?: "isMutable";
}
