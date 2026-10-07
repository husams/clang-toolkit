import type { Metadata, ServiceError, status } from "@grpc/grpc-js";

export class ClangToolkitError extends Error {
  readonly code: status;
  readonly details: string;
  readonly metadata: Metadata | undefined;

  constructor(
    code: status,
    details: string,
    metadata?: Metadata,
    cause?: unknown,
  ) {
    super(details, cause === undefined ? undefined : { cause });
    this.name = "ClangToolkitError";
    this.code = code;
    this.details = details;
    this.metadata = metadata;
  }

  static fromGrpc(error: ServiceError): ClangToolkitError {
    return new ClangToolkitError(
      error.code,
      error.details,
      error.metadata,
      error,
    );
  }
}
