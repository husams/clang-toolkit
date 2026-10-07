// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/ast/v1/semantic.proto

import type { Empty as _ctk_ast_v1_Empty, Empty__Output as _ctk_ast_v1_Empty__Output } from '../../../ctk/ast/v1/Empty.js';
import type { APSIntBits as _ctk_ast_v1_APSIntBits, APSIntBits__Output as _ctk_ast_v1_APSIntBits__Output } from '../../../ctk/ast/v1/APSIntBits.js';
import type { APFloatBits as _ctk_ast_v1_APFloatBits, APFloatBits__Output as _ctk_ast_v1_APFloatBits__Output } from '../../../ctk/ast/v1/APFloatBits.js';
import type { APFixedPointBits as _ctk_ast_v1_APFixedPointBits, APFixedPointBits__Output as _ctk_ast_v1_APFixedPointBits__Output } from '../../../ctk/ast/v1/APFixedPointBits.js';
import type { ComplexIntValue as _ctk_ast_v1_ComplexIntValue, ComplexIntValue__Output as _ctk_ast_v1_ComplexIntValue__Output } from '../../../ctk/ast/v1/ComplexIntValue.js';
import type { ComplexFloatValue as _ctk_ast_v1_ComplexFloatValue, ComplexFloatValue__Output as _ctk_ast_v1_ComplexFloatValue__Output } from '../../../ctk/ast/v1/ComplexFloatValue.js';
import type { APLValue as _ctk_ast_v1_APLValue, APLValue__Output as _ctk_ast_v1_APLValue__Output } from '../../../ctk/ast/v1/APLValue.js';
import type { APValueSequence as _ctk_ast_v1_APValueSequence, APValueSequence__Output as _ctk_ast_v1_APValueSequence__Output } from '../../../ctk/ast/v1/APValueSequence.js';
import type { APArrayValue as _ctk_ast_v1_APArrayValue, APArrayValue__Output as _ctk_ast_v1_APArrayValue__Output } from '../../../ctk/ast/v1/APArrayValue.js';
import type { APStructValue as _ctk_ast_v1_APStructValue, APStructValue__Output as _ctk_ast_v1_APStructValue__Output } from '../../../ctk/ast/v1/APStructValue.js';
import type { APUnionValue as _ctk_ast_v1_APUnionValue, APUnionValue__Output as _ctk_ast_v1_APUnionValue__Output } from '../../../ctk/ast/v1/APUnionValue.js';
import type { APMemberPointer as _ctk_ast_v1_APMemberPointer, APMemberPointer__Output as _ctk_ast_v1_APMemberPointer__Output } from '../../../ctk/ast/v1/APMemberPointer.js';
import type { APAddrLabelDiff as _ctk_ast_v1_APAddrLabelDiff, APAddrLabelDiff__Output as _ctk_ast_v1_APAddrLabelDiff__Output } from '../../../ctk/ast/v1/APAddrLabelDiff.js';

export interface APValue {
  'noObject'?: (_ctk_ast_v1_Empty | null);
  'indeterminate'?: (_ctk_ast_v1_Empty | null);
  'integer'?: (_ctk_ast_v1_APSIntBits | null);
  'floating'?: (_ctk_ast_v1_APFloatBits | null);
  'fixedPoint'?: (_ctk_ast_v1_APFixedPointBits | null);
  'complexInteger'?: (_ctk_ast_v1_ComplexIntValue | null);
  'complexFloating'?: (_ctk_ast_v1_ComplexFloatValue | null);
  'lvalue'?: (_ctk_ast_v1_APLValue | null);
  'vector'?: (_ctk_ast_v1_APValueSequence | null);
  'array'?: (_ctk_ast_v1_APArrayValue | null);
  'structure'?: (_ctk_ast_v1_APStructValue | null);
  'unionValue'?: (_ctk_ast_v1_APUnionValue | null);
  'memberPointer'?: (_ctk_ast_v1_APMemberPointer | null);
  'addressLabelDifference'?: (_ctk_ast_v1_APAddrLabelDiff | null);
  'value'?: "noObject"|"indeterminate"|"integer"|"floating"|"fixedPoint"|"complexInteger"|"complexFloating"|"lvalue"|"vector"|"array"|"structure"|"unionValue"|"memberPointer"|"addressLabelDifference";
}

export interface APValue__Output {
  'noObject'?: (_ctk_ast_v1_Empty__Output | null);
  'indeterminate'?: (_ctk_ast_v1_Empty__Output | null);
  'integer'?: (_ctk_ast_v1_APSIntBits__Output | null);
  'floating'?: (_ctk_ast_v1_APFloatBits__Output | null);
  'fixedPoint'?: (_ctk_ast_v1_APFixedPointBits__Output | null);
  'complexInteger'?: (_ctk_ast_v1_ComplexIntValue__Output | null);
  'complexFloating'?: (_ctk_ast_v1_ComplexFloatValue__Output | null);
  'lvalue'?: (_ctk_ast_v1_APLValue__Output | null);
  'vector'?: (_ctk_ast_v1_APValueSequence__Output | null);
  'array'?: (_ctk_ast_v1_APArrayValue__Output | null);
  'structure'?: (_ctk_ast_v1_APStructValue__Output | null);
  'unionValue'?: (_ctk_ast_v1_APUnionValue__Output | null);
  'memberPointer'?: (_ctk_ast_v1_APMemberPointer__Output | null);
  'addressLabelDifference'?: (_ctk_ast_v1_APAddrLabelDiff__Output | null);
  'value'?: "noObject"|"indeterminate"|"integer"|"floating"|"fixedPoint"|"complexInteger"|"complexFloating"|"lvalue"|"vector"|"array"|"structure"|"unionValue"|"memberPointer"|"addressLabelDifference";
}
