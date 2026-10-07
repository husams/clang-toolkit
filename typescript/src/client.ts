import { isAbsolute } from "node:path";
import { status } from "@grpc/grpc-js";
import { z } from "zod";
import { BindingSelection } from "./binding-selection.js";
import {
  fileOptionsSchema,
  matchOptionsSchema,
  matchResponseSchema,
  parseResponseSchema,
  scriptResponseSchema,
} from "./boundary.js";
import { ClangToolkitError } from "./clang-toolkit-error.js";
import { loadNetworkConfig } from "./configuration.js";
import type { NetworkConfiguration } from "./configuration-types.js";
import { handleOwner } from "./cursor-handle.js";
import { CursorOwner } from "./cursor-owner.js";
import type { ScriptResponse__Output } from "./generated/ctk/analysis/v1/ScriptResponse.js";
import type { FileMatchTarget } from "./generated/ctk/match/v1/FileMatchTarget.js";
import type { MatchRequest } from "./generated/ctk/match/v1/MatchRequest.js";
import type { MatchResponse__Output } from "./generated/ctk/match/v1/MatchResponse.js";
import type { ParseResponse__Output } from "./generated/ctk/match/v1/ParseResponse.js";
import { GrpcTransport } from "./grpc-transport.js";
import { snapshot } from "./immutable.js";
import { MatchValue } from "./match-value.js";
import type {
  ClientOptions,
  FileOptions,
  MatchOptions,
  ScriptOptions,
} from "./options.js";
import { ParsedTree } from "./parsed-tree.js";
import type { ScriptResult } from "./semantic-types.js";
import { TreeScope } from "./tree-scope.js";

export type MatchTarget = string | ParsedTree | BindingSelection;

export class Client implements AsyncDisposable {
  private readonly identity = {};
  private readonly transport: GrpcTransport;
  private readonly defaults: FileOptions;
  private readonly owners = new Map<string, CursorOwner>();
  private readonly pending = new Set<Promise<unknown>>();
  private closing = false;
  private closeTask: Promise<void> | undefined;
  readonly configuration: NetworkConfiguration;
  readonly endpoint: string;

  constructor();
  constructor(options: ClientOptions);
  constructor(endpoint: string, options?: ClientOptions);
  constructor(
    endpointOrOptions: string | ClientOptions = {},
    legacyOptions: ClientOptions = {},
  ) {
    const options =
      typeof endpointOrOptions === "string" ? legacyOptions : endpointOrOptions;
    this.configuration = loadNetworkConfig(options);
    this.endpoint =
      typeof endpointOrOptions === "string"
        ? z.string().min(1).parse(endpointOrOptions)
        : this.configuration.target;
    if (options.timeoutMs !== undefined && options.timeoutMs !== null)
      z.number().int().positive().safe().parse(options.timeoutMs);
    if (options.connectTimeoutMs !== undefined)
      z.number().int().positive().safe().parse(options.connectTimeoutMs);
    fileOptionsSchema.parse(options);
    this.defaults = snapshot({
      ...(options.compilationDatabase === undefined
        ? {}
        : { compilationDatabase: options.compilationDatabase }),
      ...(options.workingDirectory === undefined
        ? {}
        : { workingDirectory: options.workingDirectory }),
      ...(options.compileArguments === undefined
        ? {}
        : { compileArguments: options.compileArguments }),
    });
    this.transport = new GrpcTransport(this.endpoint, {
      ...options,
      channelOptions: {
        ...this.configuration.clientOptions,
        ...options.channelOptions,
      },
      timeoutMs:
        options.timeoutMs === undefined
          ? this.configuration.rpcTimeoutMs === null
            ? null
            : Number(this.configuration.rpcTimeoutMs)
          : options.timeoutMs,
    });
  }

  static async connect(options: ClientOptions = {}): Promise<Client> {
    const client = new Client(options);
    try {
      await client.ready(options.connectTimeoutMs ?? 30_000);
      return client;
    } catch (error) {
      try {
        await client.close();
      } catch (cleanup) {
        throw new AggregateError(
          [error, cleanup],
          "client connection and cleanup failed",
        );
      }
      throw error;
    }
  }

  private assertOpen(): void {
    if (this.closing)
      throw new ClangToolkitError(
        status.FAILED_PRECONDITION,
        "client is closed",
      );
  }

  private track<T>(task: Promise<T>): Promise<T> {
    this.pending.add(task);
    task.then(
      () => this.pending.delete(task),
      () => this.pending.delete(task),
    );
    return task;
  }

  private file(path: string, options: FileOptions): FileMatchTarget {
    z.string().min(1).parse(path);
    return {
      filePath: path,
      ...this.compilationProfile(options),
    };
  }

  private compilationProfile(options: FileOptions): {
    workingDirectory: string;
    compileArguments: string[];
    compilationDatabase: string;
  } {
    const parsed = fileOptionsSchema.parse(options);
    const directory =
      parsed.workingDirectory ??
      this.defaults.workingDirectory ??
      process.cwd();
    if (!isAbsolute(directory))
      throw new ClangToolkitError(
        status.INVALID_ARGUMENT,
        "workingDirectory must be absolute",
      );
    return {
      workingDirectory: directory,
      compilationDatabase:
        parsed.compilationDatabase ?? this.defaults.compilationDatabase ?? "",
      compileArguments: [
        ...(parsed.compileArguments ?? this.defaults.compileArguments ?? []),
      ],
    };
  }

  private own(sessionId: string, revision: string): CursorOwner {
    const existing = this.owners.get(sessionId);
    if (existing) {
      if (existing.revision !== revision)
        throw new Error(
          "server unexpectedly replaced an immutable result cursor",
        );
      return existing;
    }
    const owner = new CursorOwner(
      this.identity,
      sessionId,
      revision,
      async () => {
        await this.track(
          this.transport.invoke((metadata, options, callback) =>
            this.transport.matches.CloseSession(
              { sessionId },
              metadata,
              options,
              callback,
            ),
          ),
        );
        this.owners.delete(sessionId);
      },
      () => !this.closing,
    );
    this.owners.set(sessionId, owner);
    return owner;
  }

  ready(timeoutMs?: number): Promise<void> {
    this.assertOpen();
    return this.track(this.transport.ready(timeoutMs));
  }

  parse(path: string, options: FileOptions = {}): Promise<ParsedTree> {
    this.assertOpen();
    const file = this.file(path, options);
    return this.track(
      (async () => {
        const response = await this.transport.invoke<ParseResponse__Output>(
          (metadata, callOptions, callback) =>
            this.transport.matches.Parse(file, metadata, callOptions, callback),
        );
        parseResponseSchema.parse(response);
        return new ParsedTree(
          this.own(response.sessionId, response.resultRevision),
          path,
          {
            workingDirectory: file.workingDirectory ?? process.cwd(),
            compileArguments: [...(file.compileArguments ?? [])],
            ...(file.compilationDatabase
              ? { compilationDatabase: file.compilationDatabase }
              : {}),
          },
        );
      })(),
    );
  }

  match(
    query: string,
    target: MatchTarget,
    options: MatchOptions = {},
  ): Promise<MatchValue> {
    this.assertOpen();
    z.string()
      .min(1)
      .max(1024 * 1024)
      .parse(query);
    const parsed = matchOptionsSchema.parse(options);
    if (parsed.scope !== undefined && !(target instanceof BindingSelection))
      throw new ClangToolkitError(
        status.INVALID_ARGUMENT,
        "binding scope requires a binding target",
      );
    const request: MatchRequest = {
      query,
      preserveSource: true,
      traversalMode:
        parsed.traversal === "spelled"
          ? "MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE"
          : "MATCH_TRAVERSAL_MODE_AS_IS",
    };
    if (typeof target === "string") request.file = this.file(target, options);
    else if (
      target instanceof ParsedTree ||
      target instanceof BindingSelection
    ) {
      const owner = target[handleOwner];
      owner.assertOpen(this.identity);
      if (
        parsed.compilationDatabase !== undefined ||
        parsed.compileArguments !== undefined ||
        parsed.workingDirectory !== undefined
      )
        throw new ClangToolkitError(
          status.INVALID_ARGUMENT,
          "retained trees keep their compilation profile",
        );
      if (target instanceof ParsedTree) {
        if (parsed.scope !== undefined)
          throw new ClangToolkitError(
            status.INVALID_ARGUMENT,
            "binding scope requires a binding target",
          );
        request.session = {
          sessionId: owner.sessionId,
          expectedResultRevision: owner.revision,
        };
      } else {
        request.binding = {
          sessionId: owner.sessionId,
          expectedResultRevision: owner.revision,
          bind: target.name,
          scope:
            parsed.scope === "rootOnly"
              ? "BINDING_MATCH_SCOPE_ROOT_ONLY"
              : "BINDING_MATCH_SCOPE_SUBTREE",
          ...(target.matchIndex === undefined
            ? {}
            : { matchIndex: target.matchIndex }),
        };
      }
    } else
      throw new ClangToolkitError(
        status.INVALID_ARGUMENT,
        "match requires a file, parsed tree, or binding selection",
      );
    return this.track(
      (async () => {
        const response = await this.transport.invoke<MatchResponse__Output>(
          (metadata, callOptions, callback) =>
            this.transport.matches.Match(
              request,
              metadata,
              callOptions,
              callback,
            ),
          options.callOptions,
        );
        matchResponseSchema.parse(response);
        return new MatchValue(
          this.own(response.sessionId, response.resultRevision),
          response.results,
        );
      })(),
    );
  }

  runScript(
    source: string,
    options: ScriptOptions = {},
  ): Promise<ScriptResult> {
    this.assertOpen();
    z.string()
      .max(1024 * 1024)
      .parse(source);
    if (options.maxSteps !== undefined)
      z.number().int().min(1).max(10_000).parse(options.maxSteps);
    const file =
      options.file === undefined ? undefined : this.file(options.file, options);
    const profile =
      file === undefined ? this.compilationProfile(options) : undefined;
    return this.track(
      (async () => {
        const response = await this.transport.invoke<ScriptResponse__Output>(
          (metadata, callOptions, callback) =>
            this.transport.analyses.RunScript(
              {
                source,
                ...(file === undefined ? {} : { file }),
                ...(profile === undefined ? {} : { profile }),
                ...(options.maxSteps === undefined
                  ? {}
                  : { maxSteps: options.maxSteps }),
              },
              metadata,
              callOptions,
              callback,
            ),
          options.callOptions,
        );
        scriptResponseSchema.parse(response);
        return snapshot(response);
      })(),
    );
  }

  async withTree<T extends MatchValue | BindingSelection>(
    path: string,
    block: (scope: TreeScope) => Promise<T>,
    options: FileOptions = {},
  ): Promise<T> {
    const tree = await this.parse(path, options);
    const scope = new TreeScope(this, tree);
    let result: T;
    try {
      result = await block(scope);
      if (!(result instanceof MatchValue || result instanceof BindingSelection))
        throw new ClangToolkitError(
          status.INVALID_ARGUMENT,
          "tree scope must return a match value or binding selection",
        );
      result[handleOwner].assertOpen(this.identity);
    } catch (error) {
      try {
        await scope.finish();
      } catch (cleanup) {
        const cleanupErrors =
          cleanup instanceof AggregateError
            ? cleanup.errors.filter((failure) => failure !== error)
            : [cleanup];
        if (cleanupErrors.length === 0) throw error;
        throw new AggregateError(
          [error, ...cleanupErrors],
          "tree scope and cleanup failed",
        );
      }
      throw error;
    }
    await scope.finish(result[handleOwner]);
    return result;
  }

  close(): Promise<void> {
    if (!this.closeTask) {
      this.closing = true;
      this.closeTask = (async () => {
        await Promise.allSettled(this.pending);
        const results = await Promise.allSettled(
          [...this.owners.values()].map((owner) => owner.close()),
        );
        this.transport.close();
        const errors = results.flatMap((result) =>
          result.status === "rejected" ? [result.reason] : [],
        );
        if (errors.length)
          throw new AggregateError(errors, "failed to close native sessions");
      })();
    }
    return this.closeTask;
  }

  [Symbol.asyncDispose](): Promise<void> {
    return this.close();
  }
}
