// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { TypeInfo as _ctk_ast_v1_TypeInfo, TypeInfo__Output as _ctk_ast_v1_TypeInfo__Output } from '../../../ctk/ast/v1/TypeInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { FunctionExtInfo as _ctk_ast_v1_FunctionExtInfo, FunctionExtInfo__Output as _ctk_ast_v1_FunctionExtInfo__Output } from '../../../ctk/ast/v1/FunctionExtInfo.js';
import type { FunctionProtoExtInfo as _ctk_ast_v1_FunctionProtoExtInfo, FunctionProtoExtInfo__Output as _ctk_ast_v1_FunctionProtoExtInfo__Output } from '../../../ctk/ast/v1/FunctionProtoExtInfo.js';

export interface FunctionProtoType {
  'info'?: (_ctk_ast_v1_TypeInfo | null);
  'returnType'?: (_ctk_ast_v1_QualType | null);
  'parameterTypes'?: (_ctk_ast_v1_QualType)[];
  'isVariadic'?: (boolean);
  'extInfo'?: (_ctk_ast_v1_FunctionExtInfo | null);
  'prototypeInfo'?: (_ctk_ast_v1_FunctionProtoExtInfo | null);
  '_isVariadic'?: "isVariadic";
}

export interface FunctionProtoType__Output {
  'info': (_ctk_ast_v1_TypeInfo__Output | null);
  'returnType': (_ctk_ast_v1_QualType__Output | null);
  'parameterTypes': (_ctk_ast_v1_QualType__Output)[];
  'isVariadic'?: (boolean);
  'extInfo': (_ctk_ast_v1_FunctionExtInfo__Output | null);
  'prototypeInfo': (_ctk_ast_v1_FunctionProtoExtInfo__Output | null);
  '_isVariadic'?: "isVariadic";
}
