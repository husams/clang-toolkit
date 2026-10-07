import type { ScriptResponse__Output } from "./generated/ctk/analysis/v1/ScriptResponse.js";
import type { AstNode__Output } from "./generated/ctk/ast/v1/AstNode.js";
import type { MatchBinding__Output } from "./generated/ctk/match/v1/MatchBinding.js";
import type { MatchResult__Output } from "./generated/ctk/match/v1/MatchResult.js";

export type DeepReadonly<T> = T extends Uint8Array
  ? T
  : T extends readonly (infer Item)[]
    ? readonly DeepReadonly<Item>[]
    : T extends object
      ? { readonly [Key in keyof T]: DeepReadonly<T[Key]> }
      : T;

export type SemanticNode = DeepReadonly<AstNode__Output>;
export type SemanticBinding = DeepReadonly<MatchBinding__Output>;
export type SemanticRow = DeepReadonly<MatchResult__Output>;
export type ScriptResult = DeepReadonly<ScriptResponse__Output>;
