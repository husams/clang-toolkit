import { statSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import type { ChannelOptions } from "@grpc/grpc-js";
import { ConfigurationError } from "./configuration-error.js";
import { readConfigurationFile } from "./configuration-reader.js";
import {
  normalizeLoopback,
  validateConfiguration,
} from "./configuration-schema.js";
import type {
  ConfigurationMap,
  ConfigurationOptions,
  ConfigurationScalar,
  NetworkConfiguration,
} from "./configuration-types.js";
import { snapshot } from "./immutable.js";

const defaults: ConfigurationMap = {
  version: 1n,
  network: { transport: "unix", unix: { socket_path: null }, tcp: {} },
  pool: { size: 3n },
  queue: { size: 100n },
  session: { max_files: 100n, max_memory_bytes: 2147483648n },
  server: { grpc: { max_send_message_bytes: -1n }, shutdown_grace_ms: null },
  client: { grpc: { max_receive_message_bytes: -1n }, rpc_timeout_ms: null },
};

export function loadNetworkConfig(
  options: ConfigurationOptions = {},
): NetworkConfiguration {
  const cwd = resolve(options.cwd ?? process.cwd());
  const home = resolve(options.home ?? homedir());
  const system = resolve(options.systemDirectory ?? "/etc/clang-toolkit");
  const config = structuredClone(defaults);
  const provenance: Record<string, string> = Object.create(null);
  const flatten = (
    value: ConfigurationMap,
    prefix = "",
  ): Record<string, ConfigurationScalar> => {
    const output: Record<string, ConfigurationScalar> = Object.create(null);
    for (const [key, child] of Object.entries(value)) {
      const dotted = prefix ? `${prefix}.${key}` : key;
      if (child !== null && typeof child === "object")
        Object.assign(output, flatten(child, dotted));
      else output[dotted] = child;
    }
    return output;
  };
  for (const key of Object.keys(flatten(config)))
    provenance[key] = "<defaults>";
  const merge = (
    base: ConfigurationMap,
    layer: ConfigurationMap,
    path: string,
    prefix = "",
  ): void => {
    for (const [key, value] of Object.entries(layer)) {
      const dotted = prefix ? `${prefix}.${key}` : key;
      const previous = base[key];
      if (
        value !== null &&
        typeof value === "object" &&
        previous !== null &&
        typeof previous === "object"
      )
        merge(previous, value, path, dotted);
      else {
        base[key] = structuredClone(value);
        if (value !== null && typeof value === "object") {
          for (const leaf of Object.keys(flatten(value, dotted)))
            provenance[leaf] = path;
        } else provenance[dotted] = path;
      }
    }
  };
  const files: string[] = [];
  const load = (path: string, explicit: boolean): void => {
    try {
      if (!statSync(path).isFile())
        throw new ConfigurationError(
          path,
          "",
          "configuration path is not a file",
        );
    } catch (error) {
      if (
        !explicit &&
        error instanceof Error &&
        "code" in error &&
        error.code === "ENOENT"
      )
        return;
      if (error instanceof ConfigurationError) throw error;
      throw new ConfigurationError(
        path,
        "",
        explicit
          ? "cannot access selected configuration file"
          : "cannot access discovered configuration file",
        error,
      );
    }
    const document = readConfigurationFile(path);
    validateConfiguration(document, path);
    merge(config, document, path);
    files.push(path);
  };
  load(resolve(system, "clang-toolkit.yaml"), false);
  for (const directory of [home, cwd]) {
    load(resolve(directory, "clang-toolkit.yaml"), false);
    load(resolve(directory, ".clang-toolkit.yaml"), false);
  }
  if (options.configPath !== undefined) {
    if (
      typeof options.configPath !== "string" ||
      !options.configPath ||
      options.configPath.includes("\0")
    )
      throw new ConfigurationError(
        "configuration",
        "configPath",
        "must be a nonempty path without NUL",
      );
    load(resolve(cwd, options.configPath), true);
  }
  validateConfiguration(config, "effective configuration");
  const values = flatten(config);
  const transport = values["network.transport"] as "unix" | "tcp";
  let target: string;
  if (transport === "unix") {
    const socket = values["network.unix.socket_path"];
    const path =
      typeof socket === "string"
        ? resolve(
            dirname(provenance["network.unix.socket_path"] ?? cwd),
            socket,
          )
        : resolve(tmpdir(), "ctk.sock");
    target = `unix://${path}`;
  } else {
    const host = values["network.tcp.host"];
    const port = values["network.tcp.port"];
    if (typeof host !== "string")
      throw new ConfigurationError(
        "effective configuration",
        "network.tcp.host",
        "TCP requires an explicit host",
      );
    if (typeof port !== "bigint")
      throw new ConfigurationError(
        "effective configuration",
        "network.tcp.port",
        "TCP requires an explicit port",
      );
    const normalized = normalizeLoopback(host);
    if (!normalized)
      throw new ConfigurationError(
        provenance["network.tcp.host"] ?? "effective configuration",
        "network.tcp.host",
        "invalid loopback host",
      );
    target = `${normalized}:${port}`;
  }
  const grpcOptions = (side: string): ChannelOptions => {
    const grpc: ChannelOptions = {};
    for (const kind of ["receive", "send"] as const) {
      const value = values[`${side}.grpc.max_${kind}_message_bytes`];
      if (typeof value === "bigint")
        grpc[`grpc.max_${kind}_message_length`] = Number(value);
    }
    return grpc;
  };
  return snapshot({
    target,
    transport,
    clientOptions: grpcOptions("client"),
    serverOptions: grpcOptions("server"),
    rpcTimeoutMs: values["client.rpc_timeout_ms"] as bigint | null,
    shutdownGraceMs: values["server.shutdown_grace_ms"] as bigint | null,
    poolSize: Number(values["pool.size"]),
    queueSize: Number(values["queue.size"]),
    maxFiles: Number(values["session.max_files"]),
    maxMemoryBytes: values["session.max_memory_bytes"] as bigint,
    effectiveValues: values,
    provenance,
    files,
  });
}
