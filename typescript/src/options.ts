import type {
  CallOptions,
  ChannelCredentials,
  ChannelOptions,
  Metadata,
} from "@grpc/grpc-js";
import type { ConfigurationOptions } from "./configuration-types.js";

export interface FileOptions {
  workingDirectory?: string;
  compileArguments?: readonly string[];
  compilationDatabase?: string;
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
  callOptions?: CallOptions;
}
export interface ScriptOptions extends FileOptions {
  file?: string;
  maxSteps?: number;
  callOptions?: CallOptions;
}
