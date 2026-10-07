import { fileURLToPath } from "node:url";
import {
  type CallOptions,
  type ClientUnaryCall,
  credentials,
  loadPackageDefinition,
  Metadata,
  type requestCallback,
} from "@grpc/grpc-js";
import { loadSync } from "@grpc/proto-loader";
import { ClangToolkitError } from "./clang-toolkit-error.js";
import type { ProtoGrpcType as AnalysisPackage } from "./generated/analysis_service.js";
import type { AnalysisServiceClient } from "./generated/ctk/analysis/v1/AnalysisService.js";
import type { MatchServiceClient } from "./generated/ctk/match/v1/MatchService.js";
import type { ProtoGrpcType as MatchPackage } from "./generated/match_service.js";
import type { ClientOptions } from "./options.js";

export class GrpcTransport {
  readonly matches: MatchServiceClient;
  readonly analyses: AnalysisServiceClient;
  private readonly metadata: Metadata;
  private readonly timeoutMs: number | null;

  constructor(endpoint: string, options: ClientOptions) {
    const directory = fileURLToPath(new URL("../schema/", import.meta.url));
    const definitions = loadSync(
      [
        `${directory}match/v1/match_service.proto`,
        `${directory}analysis/v1/analysis_service.proto`,
      ],
      {
        includeDirs: [directory],
        longs: String,
        enums: String,
        defaults: true,
        oneofs: true,
      },
    );
    const loaded = loadPackageDefinition(definitions);
    const matchPackage = loaded as unknown as MatchPackage;
    const analysisPackage = loaded as unknown as AnalysisPackage;
    const channelCredentials =
      options.credentials ?? credentials.createInsecure();
    this.matches = new matchPackage.ctk.match.v1.MatchService(
      endpoint,
      channelCredentials,
      options.channelOptions,
    );
    this.analyses = new analysisPackage.ctk.analysis.v1.AnalysisService(
      endpoint,
      channelCredentials,
      options.channelOptions,
    );
    this.metadata = options.metadata?.clone() ?? new Metadata();
    this.timeoutMs = options.timeoutMs ?? null;
  }

  invoke<T>(
    start: (
      metadata: Metadata,
      options: CallOptions,
      callback: requestCallback<T>,
    ) => ClientUnaryCall,
    options?: CallOptions,
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      start(
        this.metadata.clone(),
        {
          ...(this.timeoutMs === null
            ? {}
            : { deadline: Date.now() + this.timeoutMs }),
          ...options,
        },
        (error, value) => {
          if (error) reject(ClangToolkitError.fromGrpc(error));
          else if (value === undefined)
            reject(new Error("gRPC returned no response"));
          else resolve(value);
        },
      );
    });
  }

  ready(timeoutMs = 30_000): Promise<void> {
    return new Promise((resolve, reject) => {
      this.matches.waitForReady(Date.now() + timeoutMs, (error) =>
        error ? reject(error) : resolve(),
      );
    });
  }

  close(): void {
    this.matches.close();
    this.analyses.close();
  }
}
