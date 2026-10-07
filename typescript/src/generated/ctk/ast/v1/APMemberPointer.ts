// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclarationSymbol as _ctk_ast_v1_DeclarationSymbol, DeclarationSymbol__Output as _ctk_ast_v1_DeclarationSymbol__Output } from '../../../ctk/ast/v1/DeclarationSymbol.js';

export interface APMemberPointer {
  'declaration'?: (_ctk_ast_v1_DeclarationSymbol | null);
  'path'?: (_ctk_ast_v1_DeclarationSymbol)[];
  'isDerivedMember'?: (boolean);
  '_isDerivedMember'?: "isDerivedMember";
}

export interface APMemberPointer__Output {
  'declaration': (_ctk_ast_v1_DeclarationSymbol__Output | null);
  'path': (_ctk_ast_v1_DeclarationSymbol__Output)[];
  'isDerivedMember'?: (boolean);
  '_isDerivedMember'?: "isDerivedMember";
}
