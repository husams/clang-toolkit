// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { ValueCategory as _ctk_ast_v1_ValueCategory, ValueCategory__Output as _ctk_ast_v1_ValueCategory__Output } from '../../../ctk/ast/v1/ValueCategory.js';
import type { ObjectKind as _ctk_ast_v1_ObjectKind, ObjectKind__Output as _ctk_ast_v1_ObjectKind__Output } from '../../../ctk/ast/v1/ObjectKind.js';

export interface ExprInfo {
  'type'?: (_ctk_ast_v1_QualType | null);
  'valueCategory'?: (_ctk_ast_v1_ValueCategory);
  'objectKind'?: (_ctk_ast_v1_ObjectKind);
  'isTypeDependent'?: (boolean);
  'isValueDependent'?: (boolean);
  'isInstantiationDependent'?: (boolean);
  'containsUnexpandedParameterPack'?: (boolean);
  'containsErrors'?: (boolean);
  '_valueCategory'?: "valueCategory";
  '_objectKind'?: "objectKind";
  '_isTypeDependent'?: "isTypeDependent";
  '_isValueDependent'?: "isValueDependent";
  '_isInstantiationDependent'?: "isInstantiationDependent";
  '_containsUnexpandedParameterPack'?: "containsUnexpandedParameterPack";
  '_containsErrors'?: "containsErrors";
}

export interface ExprInfo__Output {
  'type': (_ctk_ast_v1_QualType__Output | null);
  'valueCategory'?: (_ctk_ast_v1_ValueCategory__Output);
  'objectKind'?: (_ctk_ast_v1_ObjectKind__Output);
  'isTypeDependent'?: (boolean);
  'isValueDependent'?: (boolean);
  'isInstantiationDependent'?: (boolean);
  'containsUnexpandedParameterPack'?: (boolean);
  'containsErrors'?: (boolean);
  '_valueCategory'?: "valueCategory";
  '_objectKind'?: "objectKind";
  '_isTypeDependent'?: "isTypeDependent";
  '_isValueDependent'?: "isValueDependent";
  '_isInstantiationDependent'?: "isInstantiationDependent";
  '_containsUnexpandedParameterPack'?: "containsUnexpandedParameterPack";
  '_containsErrors'?: "containsErrors";
}
