// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { ExprInfo as _ctk_ast_v1_ExprInfo, ExprInfo__Output as _ctk_ast_v1_ExprInfo__Output } from '../../../ctk/ast/v1/ExprInfo.js';
import type { QualType as _ctk_ast_v1_QualType, QualType__Output as _ctk_ast_v1_QualType__Output } from '../../../ctk/ast/v1/QualType.js';
import type { OffsetOfComponent as _ctk_ast_v1_OffsetOfComponent, OffsetOfComponent__Output as _ctk_ast_v1_OffsetOfComponent__Output } from '../../../ctk/ast/v1/OffsetOfComponent.js';
import type { APIntBits as _ctk_ast_v1_APIntBits, APIntBits__Output as _ctk_ast_v1_APIntBits__Output } from '../../../ctk/ast/v1/APIntBits.js';

export interface OffsetOfExpr {
  'info'?: (_ctk_ast_v1_ExprInfo | null);
  'queriedType'?: (_ctk_ast_v1_QualType | null);
  'components'?: (_ctk_ast_v1_OffsetOfComponent)[];
  'byteOffset'?: (_ctk_ast_v1_APIntBits | null);
}

export interface OffsetOfExpr__Output {
  'info': (_ctk_ast_v1_ExprInfo__Output | null);
  'queriedType': (_ctk_ast_v1_QualType__Output | null);
  'components': (_ctk_ast_v1_OffsetOfComponent__Output)[];
  'byteOffset': (_ctk_ast_v1_APIntBits__Output | null);
}
