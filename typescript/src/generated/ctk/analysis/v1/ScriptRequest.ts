// Original file: /Users/husam/workspace/clang-toolkit/typescript/schema/analysis/v1/script_request.proto

import type { FileMatchTarget as _ctk_match_v1_FileMatchTarget, FileMatchTarget__Output as _ctk_match_v1_FileMatchTarget__Output } from '../../../ctk/match/v1/FileMatchTarget.js';
import type { ScriptCompilationProfile as _ctk_analysis_v1_ScriptCompilationProfile, ScriptCompilationProfile__Output as _ctk_analysis_v1_ScriptCompilationProfile__Output } from '../../../ctk/analysis/v1/ScriptCompilationProfile.js';
import type { ScriptValue as _ctk_analysis_v1_ScriptValue, ScriptValue__Output as _ctk_analysis_v1_ScriptValue__Output } from '../../../ctk/analysis/v1/ScriptValue.js';

export interface ScriptRequest {
  'file'?: (_ctk_match_v1_FileMatchTarget | null);
  'source'?: (string);
  'maxSteps'?: (number);
  'profile'?: (_ctk_analysis_v1_ScriptCompilationProfile | null);
  'resourceScopeId'?: (string);
  'initialValues'?: ({[key: string]: _ctk_analysis_v1_ScriptValue});
  'collectFinal'?: (boolean);
  '_maxSteps'?: "maxSteps";
}

export interface ScriptRequest__Output {
  'file': (_ctk_match_v1_FileMatchTarget__Output | null);
  'source': (string);
  'maxSteps'?: (number);
  'profile': (_ctk_analysis_v1_ScriptCompilationProfile__Output | null);
  'resourceScopeId': (string);
  'initialValues': ({[key: string]: _ctk_analysis_v1_ScriptValue__Output});
  'collectFinal': (boolean);
  '_maxSteps'?: "maxSteps";
}
