// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { CXXMethodDeclInfo as _ctk_ast_v1_CXXMethodDeclInfo, CXXMethodDeclInfo__Output as _ctk_ast_v1_CXXMethodDeclInfo__Output } from '../../../ctk/ast/v1/CXXMethodDeclInfo.js';
import type { CXXCtorInitializer as _ctk_ast_v1_CXXCtorInitializer, CXXCtorInitializer__Output as _ctk_ast_v1_CXXCtorInitializer__Output } from '../../../ctk/ast/v1/CXXCtorInitializer.js';
import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';

export interface CXXConstructorDecl {
  'method'?: (_ctk_ast_v1_CXXMethodDeclInfo | null);
  'initializers'?: (_ctk_ast_v1_CXXCtorInitializer)[];
  'isExplicit'?: (boolean);
  'isExplicitSpecifierValue'?: (boolean);
  'isConvertingConstructor'?: (boolean);
  'isCopyConstructor'?: (boolean);
  'isMoveConstructor'?: (boolean);
  'isDefaultConstructor'?: (boolean);
  'isDelegatingConstructor'?: (boolean);
  'explicitSpecifierExpression'?: (_ctk_ast_v1_ExpressionValue | null);
  '_isExplicit'?: "isExplicit";
  '_isExplicitSpecifierValue'?: "isExplicitSpecifierValue";
  '_isConvertingConstructor'?: "isConvertingConstructor";
  '_isCopyConstructor'?: "isCopyConstructor";
  '_isMoveConstructor'?: "isMoveConstructor";
  '_isDefaultConstructor'?: "isDefaultConstructor";
  '_isDelegatingConstructor'?: "isDelegatingConstructor";
}

export interface CXXConstructorDecl__Output {
  'method': (_ctk_ast_v1_CXXMethodDeclInfo__Output | null);
  'initializers': (_ctk_ast_v1_CXXCtorInitializer__Output)[];
  'isExplicit'?: (boolean);
  'isExplicitSpecifierValue'?: (boolean);
  'isConvertingConstructor'?: (boolean);
  'isCopyConstructor'?: (boolean);
  'isMoveConstructor'?: (boolean);
  'isDefaultConstructor'?: (boolean);
  'isDelegatingConstructor'?: (boolean);
  'explicitSpecifierExpression': (_ctk_ast_v1_ExpressionValue__Output | null);
  '_isExplicit'?: "isExplicit";
  '_isExplicitSpecifierValue'?: "isExplicitSpecifierValue";
  '_isConvertingConstructor'?: "isConvertingConstructor";
  '_isCopyConstructor'?: "isCopyConstructor";
  '_isMoveConstructor'?: "isMoveConstructor";
  '_isDefaultConstructor'?: "isDefaultConstructor";
  '_isDelegatingConstructor'?: "isDelegatingConstructor";
}
