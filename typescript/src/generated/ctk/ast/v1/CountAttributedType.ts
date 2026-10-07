// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { DynamicCountKind as _ctk_ast_v1_DynamicCountKind, DynamicCountKind__Output as _ctk_ast_v1_DynamicCountKind__Output } from '../../../ctk/ast/v1/DynamicCountKind.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface CountAttributedType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'wrappedType'?: (_ctk_ast_v1_QualType | null);
  'countExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  'countKind'?: (_ctk_ast_v1_DynamicCountKind);
  'coupledDeclarations'?: (_ctk_ast_v1_DeclarationSymbol)[];
  '_countKind'?: "countKind";
}

export interface CountAttributedType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'wrappedType': (_ctk_ast_v1_QualType__Output | null);
  'countExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  'countKind'?: (_ctk_ast_v1_DynamicCountKind__Output);
  'coupledDeclarations': (_ctk_ast_v1_DeclarationSymbol__Output)[];
  '_countKind'?: "countKind";
}
