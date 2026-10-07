import {
  chmodSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { afterAll, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { GrpcTransport } from "../src/grpc-transport.js";
import { Client, ConfigurationError, loadNetworkConfig } from "../src/index.js";

const fixtureSchema = z.object({
  format: z.literal(1),
  layers: z.record(z.string(), z.string()),
  cases: z.array(
    z.object({
      name: z.string(),
      files: z.record(z.string(), z.string()),
      error: z.boolean().optional(),
      error_key: z.string().optional(),
      expected: z
        .object({
          target: z.string(),
          values: z
            .record(z.string(), z.union([z.string(), z.number(), z.null()]))
            .optional(),
          origins: z.record(z.string(), z.string()).optional(),
        })
        .optional(),
    }),
  ),
});
const fixture = fixtureSchema.parse(
  JSON.parse(
    readFileSync(
      resolve(
        import.meta.dirname,
        "../../tests/fixtures/network_configuration.json",
      ),
      "utf8",
    ),
  ),
);
const temporary: string[] = [];
function paths(): {
  root: string;
  cwd: string;
  home: string;
  systemDirectory: string;
} {
  const root = mkdtempSync(resolve(tmpdir(), "ctk-ts-config-"));
  temporary.push(root);
  const output = {
    root,
    cwd: resolve(root, "project"),
    home: resolve(root, "home"),
    systemDirectory: resolve(root, "etc"),
  };
  for (const path of [
    output.cwd,
    output.home,
    output.systemDirectory,
    resolve(root, "selected"),
  ])
    mkdirSync(path);
  return output;
}
afterAll(() => {
  for (const path of temporary) rmSync(path, { recursive: true, force: true });
});

describe("shared cross-runtime YAML fixtures", () => {
  for (const scenario of fixture.cases)
    it(scenario.name, () => {
      const options = paths();
      for (const [layer, yaml] of Object.entries(scenario.files)) {
        const name = fixture.layers[layer];
        if (!name) throw new Error(`unknown fixture layer ${layer}`);
        writeFileSync(resolve(options.root, name), yaml);
      }
      const explicit =
        scenario.files.explicit === undefined
          ? {}
          : {
              configPath: resolve(
                options.root,
                fixture.layers.explicit ?? "selected/network.yaml",
              ),
            };
      const load = () => loadNetworkConfig({ ...options, ...explicit });
      if (scenario.error || scenario.error_key) {
        expect(load).toThrow(ConfigurationError);
        if (scenario.error_key) expect(load).toThrow(scenario.error_key);
        return;
      }
      const expected = scenario.expected;
      if (!expected) throw new Error("valid fixture has no expected value");
      const substitute = (value: string) =>
        value
          .replace(/\$\{ROOT\}/g, options.root)
          .replace(/\$\{TEMP\}/g, tmpdir());
      const config = load();
      expect(config.target).toBe(substitute(expected.target));
      for (const [key, value] of Object.entries(expected.values ?? {}))
        expect(config.effectiveValues[key]).toBe(
          typeof value === "number" ? BigInt(value) : value,
        );
      for (const [key, value] of Object.entries(expected.origins ?? {}))
        expect(config.provenance[key]).toBe(substitute(value));
    });
});

describe("safe data-only parser and discovery", () => {
  it("preserves explicit tagged strings and matching scalar string forms", () => {
    const options = paths();
    const configPath = resolve(options.root, "selected/network.yaml");
    for (const path of [
      "!!str 123",
      "!!str null",
      "1e3",
      "inf",
      "nan",
      "TrUe",
    ]) {
      writeFileSync(
        configPath,
        `network:\n  unix:\n    socket_path: ${path}\n`,
      );
      expect(loadNetworkConfig({ ...options, configPath }).target).toBe(
        `unix://${resolve(dirname(configPath), path.replace("!!str ", ""))}`,
      );
    }
  });

  it("supports safe aliases, null clears, and exact int64 settings", () => {
    const options = paths();
    writeFileSync(
      resolve(options.cwd, ".clang-toolkit.yaml"),
      `server:\n  grpc: &limits\n    max_receive_message_bytes: -1\nclient:\n  grpc: *limits\nsession:\n  max_memory_bytes: 9223372036854775807\n`,
    );
    const config = loadNetworkConfig(options);
    expect(config.maxMemoryBytes).toBe(9223372036854775807n);
    expect(config.clientOptions["grpc.max_receive_message_length"]).toBe(-1);
    expect(config.serverOptions["grpc.max_receive_message_length"]).toBe(-1);
    expect(Object.isFrozen(config.provenance)).toBe(true);
  });

  it("fails on absent selected files, directories, unsupported tags, multiple documents and unreadable layers", () => {
    const options = paths();
    expect(() =>
      loadNetworkConfig({ ...options, configPath: "missing.yaml" }),
    ).toThrow(ConfigurationError);
    expect(() =>
      loadNetworkConfig({ ...options, configPath: options.home }),
    ).toThrow(ConfigurationError);
    const selected = resolve(options.root, "selected/network.yaml");
    for (const yaml of [
      "pool: !unknown {size: 1}",
      "{}\n---\n{}",
      "{pool: {size: 1}}\n---",
      "pool:\n  size: +1\n",
      "pool:\n  size: !!float 1\n",
    ]) {
      writeFileSync(selected, yaml);
      expect(() =>
        loadNetworkConfig({ ...options, configPath: selected }),
      ).toThrow(ConfigurationError);
    }
    const unreadable = resolve(options.home, "clang-toolkit.yaml");
    writeFileSync(unreadable, "{}");
    chmodSync(unreadable, 0);
    try {
      expect(() => loadNetworkConfig(options)).toThrow(ConfigurationError);
    } finally {
      chmodSync(unreadable, 0o600);
    }
  });

  it("rejects excessive nesting, integer overflow and malformed inactive hosts", () => {
    const options = paths();
    const selected = resolve(options.root, "selected/network.yaml");
    const inputs = [
      `pool: ${"{size: ".repeat(65)}1${"}".repeat(65)}`,
      "session: {max_memory_bytes: 9223372036854775808}",
      "network: {tcp: {host: 192.168.1.1}}",
      "network: {tcp: {host: '[localhost]'}}",
      "network: {tcp: {host: '::1%lo0'}}",
    ];
    for (const yaml of inputs) {
      writeFileSync(selected, yaml);
      expect(() =>
        loadNetworkConfig({ ...options, configPath: selected }),
      ).toThrow(ConfigurationError);
    }
  });
});

describe("ordinary constructors and connection defaults", () => {
  it("loads config in constructors and connect without endpoint arguments", async () => {
    const options = paths();
    writeFileSync(
      resolve(options.cwd, ".clang-toolkit.yaml"),
      "network: {unix: {socket_path: custom.sock}}\nclient: {rpc_timeout_ms: 1234}",
    );
    const ready = vi
      .spyOn(GrpcTransport.prototype, "ready")
      .mockResolvedValue();
    try {
      await using configured = new Client(options);
      expect(configured.endpoint).toBe(
        `unix://${resolve(options.cwd, "custom.sock")}`,
      );
      expect(configured.configuration.rpcTimeoutMs).toBe(1234n);
      await using connected = await Client.connect(options);
      expect(connected.endpoint).toBe(configured.endpoint);
      expect(ready).toHaveBeenCalledWith(30_000);
      await using overridden = new Client("127.0.0.1:50000", options);
      expect(overridden.endpoint).toBe("127.0.0.1:50000");
      expect(overridden.configuration.target).toBe(configured.endpoint);
    } finally {
      ready.mockRestore();
    }
  });

  it("endpoint override never masks invalid configuration and unset deadlines remain unset", async () => {
    const options = paths();
    writeFileSync(
      resolve(options.home, "clang-toolkit.yaml"),
      "pool: {size: false}",
    );
    expect(() => new Client("unix:///override.sock", options)).toThrow(
      ConfigurationError,
    );
    const wire = new GrpcTransport("unix:///unused", {});
    try {
      await wire.invoke((_metadata, callOptions, callback) => {
        expect(callOptions.deadline).toBeUndefined();
        callback(null, {});
        return {} as ReturnType<GrpcTransport["matches"]["Match"]>;
      });
    } finally {
      wire.close();
    }
  });
});
