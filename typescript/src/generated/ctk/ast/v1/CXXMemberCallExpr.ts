// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { CallExprInfo as _ctk_ast_v1_CallExprInfo, CallExprInfo__Output as _ctk_ast_v1_CallExprInfo__Output } from '../../../ctk/ast/v1/CallExprInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface CXXMemberCallExpr {
  'call'?: (_ctk_ast_v1_CallExprInfo | null);
  'implicitObjectArgument'?: (_ctk_ast_v1_ExpressionValue | null);
  'objectType'?: (_ctk_ast_v1_QualType | null);
  'methodDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'recordDeclaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
}

export interface CXXMemberCallExpr__Output {
  'call': (_ctk_ast_v1_CallExprInfo__Output | null);
  'implicitObjectArgument': (_ctk_ast_v1_ExpressionValue__Output | null);
  'objectType': (_ctk_ast_v1_QualType__Output | null);
  'methodDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'recordDeclaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
}
