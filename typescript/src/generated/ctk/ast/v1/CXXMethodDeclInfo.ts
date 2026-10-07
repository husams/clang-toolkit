// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { FunctionDeclInfo as _ctk_ast_v1_FunctionDeclInfo, FunctionDeclInfo__Output as _ctk_ast_v1_FunctionDeclInfo__Output } from '../../../ctk/ast/v1/FunctionDeclInfo.js';
import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';
import type { RefQualifier as _ctk_ast_v1_RefQualifier, RefQualifier__Output as _ctk_ast_v1_RefQualifier__Output } from '../../../ctk/ast/v1/RefQualifier.js';

export interface CXXMethodDeclInfo {
  'function'?: (_ctk_ast_v1_FunctionDeclInfo | null);
  'parentRecord'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'isStatic'?: (boolean);
  'isVirtual'?: (boolean);
  'isConst'?: (boolean);
  'isVolatile'?: (boolean);
  'refQualifier'?: (_ctk_ast_v1_RefQualifier);
  'overriddenMethods'?: (_ctk_ast_v1_DeclarationSymbol)[];
  '_isStatic'?: "isStatic";
  '_isVirtual'?: "isVirtual";
  '_isConst'?: "isConst";
  '_isVolatile'?: "isVolatile";
  '_refQualifier'?: "refQualifier";
}

export interface CXXMethodDeclInfo__Output {
  'function': (_ctk_ast_v1_FunctionDeclInfo__Output | null);
  'parentRecord': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'isStatic'?: (boolean);
  'isVirtual'?: (boolean);
  'isConst'?: (boolean);
  'isVolatile'?: (boolean);
  'refQualifier'?: (_ctk_ast_v1_RefQualifier__Output);
  'overriddenMethods': (_ctk_ast_v1_DeclarationSymbol__Output)[];
  '_isStatic'?: "isStatic";
  '_isVirtual'?: "isVirtual";
  '_isConst'?: "isConst";
  '_isVolatile'?: "isVolatile";
  '_refQualifier'?: "refQualifier";
}
