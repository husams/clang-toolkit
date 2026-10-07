import { status } from "@grpc/grpc-js";
import { ClangToolkitError } from "./clang-toolkit-error.js";

export class CursorOwner {
  private closeTask: Promise<void> | undefined;
  private disposed = false;

  constructor(
    readonly identity: object,
    readonly sessionId: string,
    readonly revision: string,
    private readonly release: () => Promise<void>,
    private readonly clientOpen: () => boolean,
  ) {}

  get closed(): boolean {
    return this.disposed || !this.clientOpen();
  }

  assertOpen(identity: object): void {
    if (identity !== this.identity)
      throw new ClangToolkitError(
        status.INVALID_ARGUMENT,
        "handle belongs to another client",
      );
    if (this.closed)
      throw new ClangToolkitError(
        status.FAILED_PRECONDITION,
        "native handle is closed",
      );
  }

  close(): Promise<void> {
    if (!this.closeTask) {
      this.disposed = true;
      this.closeTask = this.release();
    }
    return this.closeTask;
  }
}
