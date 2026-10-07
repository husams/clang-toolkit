// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/common.proto

import type { AddressSpace as _ctk_ast_v1_AddressSpace, AddressSpace__Output as _ctk_ast_v1_AddressSpace__Output } from '../../../ctk/ast/v1/AddressSpace.js';

export interface Qualifiers {
  'isConst'?: (boolean);
  'isVolatile'?: (boolean);
  'isRestrict'?: (boolean);
  'isUnaligned'?: (boolean);
  'addressSpace'?: (_ctk_ast_v1_AddressSpace | null);
  '_isConst'?: "isConst";
  '_isVolatile'?: "isVolatile";
  '_isRestrict'?: "isRestrict";
  '_isUnaligned'?: "isUnaligned";
}

export interface Qualifiers__Output {
  'isConst'?: (boolean);
  'isVolatile'?: (boolean);
  'isRestrict'?: (boolean);
  'isUnaligned'?: (boolean);
  'addressSpace': (_ctk_ast_v1_AddressSpace__Output | null);
  '_isConst'?: "isConst";
  '_isVolatile'?: "isVolatile";
  '_isRestrict'?: "isRestrict";
  '_isUnaligned'?: "isUnaligned";
}
