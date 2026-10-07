// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { SymbolKind as _ctk_ast_v1_SymbolKind, SymbolKind__Output as _ctk_ast_v1_SymbolKind__Output } from '../../../ctk/ast/v1/SymbolKind.js';
import type { TypeDescription as _ctk_ast_v1_TypeDescription, TypeDescription__Output as _ctk_ast_v1_TypeDescription__Output } from '../../../ctk/ast/v1/TypeDescription.js';
import type { FunctionSignature as _ctk_ast_v1_FunctionSignature, FunctionSignature__Output as _ctk_ast_v1_FunctionSignature__Output } from '../../../ctk/ast/v1/FunctionSignature.js';
import type { TemplateArgumentDescription as _ctk_ast_v1_TemplateArgumentDescription, TemplateArgumentDescription__Output as _ctk_ast_v1_TemplateArgumentDescription__Output } from '../../../ctk/ast/v1/TemplateArgumentDescription.js';
import type { OverloadedOperatorKind as _ctk_ast_v1_OverloadedOperatorKind, OverloadedOperatorKind__Output as _ctk_ast_v1_OverloadedOperatorKind__Output } from '../../../ctk/ast/v1/OverloadedOperatorKind.js';

export interface DeclarationSymbol {
  'name'?: (string);
  'qualifiedName'?: (string);
  'kind'?: (_ctk_ast_v1_SymbolKind);
  'type'?: (_ctk_ast_v1_TypeDescription | null);
  'function'?: (_ctk_ast_v1_FunctionSignature | null);
  'clangClass'?: (string);
  'templateArguments'?: (_ctk_ast_v1_TemplateArgumentDescription)[];
  'isParameterPack'?: (boolean);
  'overloadedOperator'?: (_ctk_ast_v1_OverloadedOperatorKind);
  '_name'?: "name";
  '_qualifiedName'?: "qualifiedName";
  '_kind'?: "kind";
  '_clangClass'?: "clangClass";
  '_isParameterPack'?: "isParameterPack";
  '_overloadedOperator'?: "overloadedOperator";
}

export interface DeclarationSymbol__Output {
  'name'?: (string);
  'qualifiedName'?: (string);
  'kind'?: (_ctk_ast_v1_SymbolKind__Output);
  'type': (_ctk_ast_v1_TypeDescription__Output | null);
  'function': (_ctk_ast_v1_FunctionSignature__Output | null);
  'clangClass'?: (string);
  'templateArguments': (_ctk_ast_v1_TemplateArgumentDescription__Output)[];
  'isParameterPack'?: (boolean);
  'overloadedOperator'?: (_ctk_ast_v1_OverloadedOperatorKind__Output);
  '_name'?: "name";
  '_qualifiedName'?: "qualifiedName";
  '_kind'?: "kind";
  '_clangClass'?: "clangClass";
  '_isParameterPack'?: "isParameterPack";
  '_overloadedOperator'?: "overloadedOperator";
}
