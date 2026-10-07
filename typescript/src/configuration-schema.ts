import { isIP } from "node:net";
import { ConfigurationError } from "./configuration-error.js";
import type {
  ConfigurationMap,
  ConfigurationScalar,
} from "./configuration-types.js";

const allowed: Record<string, readonly string[]> = {
  "": ["version", "network", "pool", "queue", "server", "session", "client"],
  network: ["transport", "unix", "tcp"],
  "network.unix": ["socket_path"],
  "network.tcp": ["host", "port"],
  pool: ["size"],
  queue: ["size"],
  session: ["max_files", "max_memory_bytes"],
  server: ["grpc", "shutdown_grace_ms"],
  client: ["grpc", "rpc_timeout_ms"],
  "server.grpc": ["max_receive_message_bytes", "max_send_message_bytes"],
  "client.grpc": ["max_receive_message_bytes", "max_send_message_bytes"],
};
const INT64_MAX = (1n << 63n) - 1n;
const INT32_MAX = (1n << 31n) - 1n;

export function normalizeLoopback(host: string): string | undefined {
  if (host === "localhost") return host;
  const bare =
    host.startsWith("[") && host.endsWith("]") ? host.slice(1, -1) : host;
  if (
    bare.includes("[") ||
    bare.includes("]") ||
    bare.includes("%") ||
    bare.includes("\0")
  )
    return undefined;
  if (isIP(bare) === 4) return bare.startsWith("127.") ? bare : undefined;
  if (isIP(bare) === 6) {
    const normalized = new URL(`http://[${bare}]/`).hostname;
    return normalized === "[::1]" ? normalized : undefined;
  }
  return undefined;
}

export function validateConfiguration(
  config: ConfigurationMap,
  source: string,
): void {
  const error = (key: string, message: string): never => {
    throw new ConfigurationError(source, key, message);
  };
  const integer = (
    value: ConfigurationScalar,
    key: string,
    min = 1n,
    max = INT64_MAX,
    nullable = false,
  ): void => {
    if (value === null && nullable) return;
    if (typeof value !== "bigint" || value < min || value > max)
      error(
        key,
        `must be a base-10 integer from ${min} to ${max}${nullable ? " or null" : ""}`,
      );
  };
  const walk = (value: ConfigurationMap, prefix: string): void => {
    for (const [key, child] of Object.entries(value)) {
      const dotted = prefix ? `${prefix}.${key}` : key;
      if (!allowed[prefix]?.includes(key))
        error(dotted, "unknown configuration key");
      if (Object.hasOwn(allowed, dotted)) {
        if (child === null || typeof child !== "object")
          error(dotted, "must be a mapping");
        walk(child as ConfigurationMap, dotted);
        continue;
      }
      if (typeof child === "object" && child !== null)
        error(dotted, "must be a scalar");
      const scalar = child as ConfigurationScalar;
      switch (dotted) {
        case "version":
          if (scalar !== 1n) error(dotted, "must be integer 1");
          break;
        case "network.transport":
          if (scalar !== "unix" && scalar !== "tcp")
            error(dotted, "must be unix or tcp");
          break;
        case "network.unix.socket_path":
          if (scalar !== null && (typeof scalar !== "string" || !scalar))
            error(dotted, "must be null or a nonempty path");
          break;
        case "network.tcp.host":
          if (typeof scalar !== "string" || !normalizeLoopback(scalar))
            error(dotted, "must be localhost or a loopback IPv4/IPv6 address");
          break;
        case "network.tcp.port":
          integer(scalar, dotted, 1n, 65535n);
          break;
        case "pool.size":
        case "queue.size":
        case "session.max_files":
          integer(scalar, dotted, 1n, INT32_MAX);
          break;
        case "session.max_memory_bytes":
          integer(scalar, dotted);
          break;
        case "client.rpc_timeout_ms":
          integer(scalar, dotted, 1n, INT64_MAX, true);
          break;
        case "server.shutdown_grace_ms":
          integer(scalar, dotted, 0n, INT64_MAX, true);
          break;
        default:
          if (scalar !== -1n) integer(scalar, dotted, 1n, INT32_MAX, true);
      }
    }
  };
  walk(config, "");
}
