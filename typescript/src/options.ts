import type {
  CallOptions,
  ChannelCredentials,
  ChannelOptions,
  Metadata,
} from "@grpc/grpc-js";
import type { ConfigurationOptions } from "./configuration-types.js";
import type { SemanticRow } from "./semantic-types.js";

export interface FileOptions {
  workingDirectory?: string;
  compileArguments?: readonly string[];
  compilationDatabase?: string;
}
export interface CppSnippetOptions extends FileOptions {
  /** Existing server-side source file whose compilation command is borrowed. */
  file?: string;
  includes?: readonly string[];
  /** Parse complete top-level C++ source instead of statements in a function. */
  translationUnit?: boolean;
}
export interface ClientOptions extends FileOptions, ConfigurationOptions {
  credentials?: ChannelCredentials;
  channelOptions?: ChannelOptions;
  metadata?: Metadata;
  timeoutMs?: number | null;
  connectTimeoutMs?: number;
}
export interface MatchOptions extends FileOptions {
  traversal?: "asIs" | "spelled";
  scope?: "subtree" | "rootOnly";
  onRow?: (row: SemanticRow, index: number) => void | Promise<void>;
  callOptions?: CallOptions;
}
export interface ScriptOptions extends FileOptions {
  file?: string;
  maxSteps?: number;
  callOptions?: CallOptions;
}
