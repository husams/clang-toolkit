// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { Qualifiers as _ctk_ast_v1_Qualifiers, Qualifiers__Output as _ctk_ast_v1_Qualifiers__Output } from '../../../ctk/ast/v1/Qualifiers.js';

export interface TypeDescription {
  'spelling'?: (string);
  'canonicalSpelling'?: (string);
  'qualifiers'?: (_ctk_ast_v1_Qualifiers | null);
  'isDependent'?: (boolean);
  '_spelling'?: "spelling";
  '_canonicalSpelling'?: "canonicalSpelling";
  '_isDependent'?: "isDependent";
}

export interface TypeDescription__Output {
  'spelling'?: (string);
  'canonicalSpelling'?: (string);
  'qualifiers': (_ctk_ast_v1_Qualifiers__Output | null);
  'isDependent'?: (boolean);
  '_spelling'?: "spelling";
  '_canonicalSpelling'?: "canonicalSpelling";
  '_isDependent'?: "isDependent";
}
