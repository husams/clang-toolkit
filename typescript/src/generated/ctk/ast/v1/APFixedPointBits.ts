// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { APIntBits as _ctk_ast_v1_APIntBits, APIntBits__Output as _ctk_ast_v1_APIntBits__Output } from '../../../ctk/ast/v1/APIntBits.js';

export interface APFixedPointBits {
  'bitPattern'?: (_ctk_ast_v1_APIntBits | null);
  'scale'?: (number);
  'isUnsigned'?: (boolean);
  'isSaturated'?: (boolean);
  'hasUnsignedPadding'?: (boolean);
  '_scale'?: "scale";
  '_isUnsigned'?: "isUnsigned";
  '_isSaturated'?: "isSaturated";
  '_hasUnsignedPadding'?: "hasUnsignedPadding";
}

export interface APFixedPointBits__Output {
  'bitPattern': (_ctk_ast_v1_APIntBits__Output | null);
  'scale'?: (number);
  'isUnsigned'?: (boolean);
  'isSaturated'?: (boolean);
  'hasUnsignedPadding'?: (boolean);
  '_scale'?: "scale";
  '_isUnsigned'?: "isUnsigned";
  '_isSaturated'?: "isSaturated";
  '_hasUnsignedPadding'?: "hasUnsignedPadding";
}
