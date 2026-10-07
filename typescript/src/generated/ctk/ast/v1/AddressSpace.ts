// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/common.proto

import type { Empty as _ctk_ast_v1_Empty, Empty__Output as _ctk_ast_v1_Empty__Output } from '../../../ctk/ast/v1/Empty.js';

export interface AddressSpace {
  'defaultSpace'?: (_ctk_ast_v1_Empty | null);
  'targetSpace'?: (number);
  'languageSpace'?: (string);
  'value'?: "defaultSpace"|"targetSpace"|"languageSpace";
}

export interface AddressSpace__Output {
  'defaultSpace'?: (_ctk_ast_v1_Empty__Output | null);
  'targetSpace'?: (number);
  'languageSpace'?: (string);
  'value'?: "defaultSpace"|"targetSpace"|"languageSpace";
}
