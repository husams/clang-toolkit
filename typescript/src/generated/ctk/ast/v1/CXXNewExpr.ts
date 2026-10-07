// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CXXNewExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'operatorNew'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'operatorDelete'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'allocatedType'?: (_ctk_ast_v1_QualType | null);
  'arraySize'?: (_ctk_ast_v1_ExpressionValue | null);
  'initializer'?: (_ctk_ast_v1_ExpressionValue | null);
  'isArray'?: (boolean);
  'isGlobalNew'?: (boolean);
  'isNothrow'?: (boolean);
  'isPlacement'?: (boolean);
  'placementArguments'?: (_ctk_ast_v1_ExpressionValue)[];
  '_isArray'?: "isArray";
  '_isGlobalNew'?: "isGlobalNew";
  '_isNothrow'?: "isNothrow";
  '_isPlacement'?: "isPlacement";
}

export interface CXXNewExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'operatorNew': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'operatorDelete': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'allocatedType': (_ctk_ast_v1_QualType__Output | null);
  'arraySize': (_ctk_ast_v1_ExpressionValue__Output | null);
  'initializer': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isArray'?: (boolean);
  'isGlobalNew'?: (boolean);
  'isNothrow'?: (boolean);
  'isPlacement'?: (boolean);
  'placementArguments': (_ctk_ast_v1_ExpressionValue__Output)[];
  '_isArray'?: "isArray";
  '_isGlobalNew'?: "isGlobalNew";
  '_isNothrow'?: "isNothrow";
  '_isPlacement'?: "isPlacement";
}
