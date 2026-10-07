// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclaratorDeclInfo as _ctk_ast_v1_DeclaratorDeclInfo, DeclaratorDeclInfo__Output as _ctk_ast_v1_DeclaratorDeclInfo__Output } from '../../../ctk/ast/v1/DeclaratorDeclInfo.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface FieldDecl {
  'declarator'?: (_ctk_ast_v1_DeclaratorDeclInfo | null);
  'bitWidth'?: (_ctk_ast_v1_ExpressionValue | null);
  'inClassInitializer'?: (_ctk_ast_v1_ExpressionValue | null);
  'isMutable'?: (boolean);
  'isBitField'?: (boolean);
  'isAnonymousStructOrUnion'?: (boolean);
  '_isMutable'?: "isMutable";
  '_isBitField'?: "isBitField";
  '_isAnonymousStructOrUnion'?: "isAnonymousStructOrUnion";
}

export interface FieldDecl__Output {
  'declarator': (_ctk_ast_v1_DeclaratorDeclInfo__Output | null);
  'bitWidth': (_ctk_ast_v1_ExpressionValue__Output | null);
  'inClassInitializer': (_ctk_ast_v1_ExpressionValue__Output | null);
  'isMutable'?: (boolean);
  'isBitField'?: (boolean);
  'isAnonymousStructOrUnion'?: (boolean);
  '_isMutable'?: "isMutable";
  '_isBitField'?: "isBitField";
  '_isAnonymousStructOrUnion'?: "isAnonymousStructOrUnion";
}
