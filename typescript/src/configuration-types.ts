import type { ChannelOptions } from "@grpc/grpc-js";

export interface ConfigurationOptions {
  configPath?: string;
  cwd?: string;
  home?: string;
  systemDirectory?: string;
}

export type ConfigurationScalar = string | bigint | null;
export interface ConfigurationMap {
  [key: string]: ConfigurationScalar | ConfigurationMap;
}

export interface NetworkConfiguration {
  readonly target: string;
  readonly transport: "unix" | "tcp";
  readonly clientOptions: Readonly<ChannelOptions>;
  readonly serverOptions: Readonly<ChannelOptions>;
  readonly rpcTimeoutMs: bigint | null;
  readonly shutdownGraceMs: bigint | null;
  readonly poolSize: number;
  readonly queueSize: number;
  readonly maxFiles: number;
  readonly maxMemoryBytes: bigint;
  readonly effectiveValues: Readonly<Record<string, ConfigurationScalar>>;
  readonly provenance: Readonly<Record<string, string>>;
  readonly files: readonly string[];
}
