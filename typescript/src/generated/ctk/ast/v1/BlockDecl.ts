// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { DeclInfo as _ctk_ast_v1_DeclInfo, DeclInfo__Output as _ctk_ast_v1_DeclInfo__Output } from '../../../ctk/ast/v1/DeclInfo.js';
import type { DeclarationValue as _ctk_ast_v1_DeclarationValue, DeclarationValue__Output as _ctk_ast_v1_DeclarationValue__Output } from '../../../ctk/ast/v1/DeclarationValue.js';
import type { StatementValue as _ctk_ast_v1_StatementValue, StatementValue__Output as _ctk_ast_v1_StatementValue__Output } from '../../../ctk/ast/v1/StatementValue.js';
import type { BlockCaptureInfo as _ctk_ast_v1_BlockCaptureInfo, BlockCaptureInfo__Output as _ctk_ast_v1_BlockCaptureInfo__Output } from '../../../ctk/ast/v1/BlockCaptureInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';

export interface BlockDecl {
  'declaration'?: (_ctk_ast_v1_DeclInfo | null);
  'parameters'?: (_ctk_ast_v1_DeclarationValue)[];
  'body'?: (_ctk_ast_v1_StatementValue | null);
  'captures'?: (_ctk_ast_v1_BlockCaptureInfo)[];
  'isVariadic'?: (boolean);
  'signature'?: (_ctk_ast_v1_QualType | null);
  '_isVariadic'?: "isVariadic";
}

export interface BlockDecl__Output {
  'declaration': (_ctk_ast_v1_DeclInfo__Output | null);
  'parameters': (_ctk_ast_v1_DeclarationValue__Output)[];
  'body': (_ctk_ast_v1_StatementValue__Output | null);
  'captures': (_ctk_ast_v1_BlockCaptureInfo__Output)[];
  'isVariadic'?: (boolean);
  'signature': (_ctk_ast_v1_QualType__Output | null);
  '_isVariadic'?: "isVariadic";
}
