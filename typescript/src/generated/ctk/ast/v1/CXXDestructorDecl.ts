// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { CXXMethodDeclInfo as _ctk_ast_v1_CXXMethodDeclInfo, CXXMethodDeclInfo__Output as _ctk_ast_v1_CXXMethodDeclInfo__Output } from '../../../ctk/ast/v1/CXXMethodDeclInfo.js';

export interface CXXDestructorDecl {
  'method'?: (_ctk_ast_v1_CXXMethodDeclInfo | null);
  'isTrivial'?: (boolean);
  '_isTrivial'?: "isTrivial";
}

export interface CXXDestructorDecl__Output {
  'method': (_ctk_ast_v1_CXXMethodDeclInfo__Output | null);
  'isTrivial'?: (boolean);
  '_isTrivial'?: "isTrivial";
}
