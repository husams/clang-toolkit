import { readFileSync } from "node:fs";
import { TextDecoder } from "node:util";
import { isAlias, isMap, isScalar, isSeq, parseAllDocuments } from "yaml";
import { ConfigurationError } from "./configuration-error.js";
import type {
  ConfigurationMap,
  ConfigurationScalar,
} from "./configuration-types.js";

export function readConfigurationFile(path: string): ConfigurationMap {
  let source: string;
  try {
    source = new TextDecoder("utf-8", { fatal: true }).decode(
      readFileSync(path),
    );
  } catch (error) {
    throw new ConfigurationError(
      path,
      "",
      "cannot read UTF-8 configuration file",
      error,
    );
  }
  const documents = parseAllDocuments(source, {
    version: "1.1",
    schema: "yaml-1.1",
    intAsBigInt: true,
    uniqueKeys: true,
    merge: false,
    // Match the shared PyYAML YAML-1.1 implicit float subset; bare 1e3 is
    // a string there. The official YAML parser still owns tokenization/ASTs.
    customTags: (tags) =>
      tags.map((tag) =>
        typeof tag === "object" &&
        tag.collection === undefined &&
        tag.tag === "tag:yaml.org,2002:float"
          ? {
              ...tag,
              test: /^(?:[-+]?[0-9][0-9_]*\.[0-9_]*(?:[eE][-+][0-9]+)?|\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?|[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$/,
            }
          : tag,
      ),
  });
  if (documents.length !== 1)
    throw new ConfigurationError(
      path,
      "",
      "exactly one YAML mapping document is required",
    );
  const document = documents[0];
  if (!document) throw new ConfigurationError(path, "", "empty YAML document");
  if (document.errors.length || document.warnings.length)
    throw new ConfigurationError(
      path,
      "",
      [...document.errors, ...document.warnings]
        .map((error) => error.message)
        .join("; "),
    );
  const active = new Set<object>();
  let visits = 0;
  const convert = (
    node: unknown,
    key: string,
    depth: number,
  ): ConfigurationScalar | ConfigurationMap => {
    if (depth >= 64 || ++visits > 100_000)
      throw new ConfigurationError(
        path,
        key,
        "YAML nesting or alias expansion exceeds supported limits",
      );
    if (node === null) return null;
    if (isAlias(node)) {
      const resolved = node.resolve(document);
      if (!resolved)
        throw new ConfigurationError(path, key, "unresolved YAML alias");
      return convert(resolved, key, depth);
    }
    if (typeof node !== "object" || node === null)
      throw new ConfigurationError(path, key, "invalid YAML node");
    if (active.has(node))
      throw new ConfigurationError(
        path,
        key,
        "recursive YAML aliases are not supported",
      );
    active.add(node);
    try {
      if (isSeq(node))
        throw new ConfigurationError(
          path,
          key,
          "sequences are not valid configuration values",
        );
      if (isMap(node)) {
        if (node.tag && node.tag !== "tag:yaml.org,2002:map")
          throw new ConfigurationError(
            path,
            key,
            "unsupported YAML mapping tag",
          );
        const result: ConfigurationMap = Object.create(null);
        for (const pair of node.items) {
          if (!isScalar(pair.key) || typeof pair.key.value !== "string")
            throw new ConfigurationError(
              path,
              key,
              "mapping keys must be strings",
            );
          const name = pair.key.value;
          if (name.includes("\0"))
            throw new ConfigurationError(
              path,
              key,
              "mapping keys cannot contain NUL",
            );
          if (Object.hasOwn(result, name))
            throw new ConfigurationError(
              path,
              key,
              `duplicate YAML key '${name}'`,
            );
          result[name] = convert(
            pair.value,
            key ? `${key}.${name}` : name,
            depth + 1,
          );
        }
        return result;
      }
      if (!isScalar(node))
        throw new ConfigurationError(path, key, "unsupported YAML node");
      if (
        node.tag &&
        ![
          "tag:yaml.org,2002:str",
          "tag:yaml.org,2002:int",
          "tag:yaml.org,2002:null",
        ].includes(node.tag)
      )
        throw new ConfigurationError(path, key, "unsupported YAML scalar tag");
      if (node.value === null) return null;
      if (typeof node.value === "bigint") {
        if (!/^-?[0-9]+$/.test(node.source ?? ""))
          throw new ConfigurationError(
            path,
            key,
            "integers must use base-10 notation",
          );
        return BigInt(node.source ?? "");
      }
      if (typeof node.value !== "string")
        throw new ConfigurationError(
          path,
          key,
          "unsupported scalar type; use a string or base-10 integer",
        );
      if (node.value.includes("\0"))
        throw new ConfigurationError(
          path,
          key,
          "embedded NUL is not supported",
        );
      return node.value;
    } finally {
      active.delete(node);
    }
  };
  const converted = convert(document.contents, "", 0);
  if (converted === null || typeof converted !== "object")
    throw new ConfigurationError(path, "", "document root must be a mapping");
  return converted;
}
