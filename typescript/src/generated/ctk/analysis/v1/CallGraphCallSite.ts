// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/call_graph_response.proto

import type { ExpressionValue as _ctk_ast_v1_ExpressionValue, ExpressionValue__Output as _ctk_ast_v1_ExpressionValue__Output } from '../../../ctk/ast/v1/ExpressionValue.js';
import type { MatchSourcePoint as _ctk_match_v1_MatchSourcePoint, MatchSourcePoint__Output as _ctk_match_v1_MatchSourcePoint__Output } from '../../../ctk/match/v1/MatchSourcePoint.js';
import type { MatchSourceRange as _ctk_match_v1_MatchSourceRange, MatchSourceRange__Output as _ctk_match_v1_MatchSourceRange__Output } from '../../../ctk/match/v1/MatchSourceRange.js';
import type { CallSiteFacts as _ctk_match_v1_CallSiteFacts, CallSiteFacts__Output as _ctk_match_v1_CallSiteFacts__Output } from '../../../ctk/match/v1/CallSiteFacts.js';
import type { FieldAvailability as _ctk_ast_v1_FieldAvailability, FieldAvailability__Output as _ctk_ast_v1_FieldAvailability__Output } from '../../../ctk/ast/v1/FieldAvailability.js';
import type { Long } from '@grpc/proto-loader';

export interface CallGraphCallSite {
  'callerNode'?: (number | string | Long);
  'calleeNode'?: (number | string | Long);
  'call'?: (_ctk_ast_v1_ExpressionValue | null);
  'location'?: (_ctk_match_v1_MatchSourcePoint | null);
  'range'?: (_ctk_match_v1_MatchSourceRange | null);
  'facts'?: (_ctk_match_v1_CallSiteFacts | null);
  'isComplete'?: (boolean);
  'availability'?: (_ctk_ast_v1_FieldAvailability)[];
  '_calleeNode'?: "calleeNode";
  '_isComplete'?: "isComplete";
}

export interface CallGraphCallSite__Output {
  'callerNode': (string);
  'calleeNode'?: (string);
  'call': (_ctk_ast_v1_ExpressionValue__Output | null);
  'location': (_ctk_match_v1_MatchSourcePoint__Output | null);
  'range': (_ctk_match_v1_MatchSourceRange__Output | null);
  'facts': (_ctk_match_v1_CallSiteFacts__Output | null);
  'isComplete'?: (boolean);
  'availability': (_ctk_ast_v1_FieldAvailability__Output)[];
  '_calleeNode'?: "calleeNode";
  '_isComplete'?: "isComplete";
}
