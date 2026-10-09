import {
  type ClientReadableStream,
  type StatusObject,
  status,
} from "@grpc/grpc-js";
import { matchStreamEventSchema } from "./boundary.js";
import { ClangToolkitError } from "./clang-toolkit-error.js";
import type { MatchStreamEvent__Output } from "./generated/ctk/match/v1/MatchStreamEvent.js";
import { snapshot } from "./immutable.js";
import type { MatchRowStore } from "./match-row-store.js";
import type { SemanticRow } from "./semantic-types.js";

export type MatchRowCallback = (
  row: SemanticRow,
  index: number,
) => void | Promise<void>;

export interface MatchStreamCompletion {
  sessionId: string;
  resultRevision: string;
  rowCount: string;
}

export async function consumeMatchStream(
  stream: ClientReadableStream<MatchStreamEvent__Output>,
  rows: MatchRowStore,
  onCompletion: (completion: MatchStreamCompletion) => void,
  onRow?: MatchRowCallback,
): Promise<void> {
  return new Promise((resolve, reject) => {
    let completed: MatchStreamCompletion | undefined;
    let statusObject: StatusObject | undefined;
    let ended = false;
    let settled = false;
    let processing = 0;

    const fail = (error: unknown): void => {
      if (settled) return;
      settled = true;
      try {
        stream.cancel();
      } catch (cancelError) {
        reject(
          new AggregateError(
            [error, cancelError],
            "match stream failed and could not be cancelled",
          ),
        );
        return;
      }
      reject(error);
    };

    const finishIfReady = (): void => {
      if (settled || processing !== 0 || !ended || statusObject === undefined)
        return;
      if (statusObject.code !== status.OK) {
        fail(
          new ClangToolkitError(
            statusObject.code,
            statusObject.details,
            statusObject.metadata,
          ),
        );
        return;
      }
      if (completed === undefined) {
        fail(new Error("match stream ended without a completion event"));
        return;
      }
      if (BigInt(completed.rowCount) !== BigInt(rows.length)) {
        fail(new Error("match stream row count does not match its completion"));
        return;
      }
      try {
        rows.seal();
        settled = true;
        resolve();
      } catch (error) {
        fail(error);
      }
    };

    stream.on("data", (raw: MatchStreamEvent__Output) => {
      if (settled) return;
      stream.pause();
      processing += 1;
      void (async () => {
        const event = matchStreamEventSchema.parse(raw);
        if (event.event === "row") {
          if (completed !== undefined)
            throw new Error("match stream emitted a row after completion");
          const row = raw.row;
          if (row === undefined || row === null)
            throw new Error("match stream row payload is missing");
          const index = rows.length;
          await rows.append(row);
          if (onRow !== undefined) await onRow(snapshot(row), index);
          return;
        }
        if (completed !== undefined)
          throw new Error("match stream emitted more than one completion");
        const value = event.completed;
        if (value === undefined)
          throw new Error("match stream completion payload is missing");
        completed = {
          sessionId: value.sessionId,
          resultRevision: value.resultRevision,
          rowCount: value.rowCount,
        };
        onCompletion(completed);
      })().then(
        () => {
          processing -= 1;
          if (settled) return;
          try {
            stream.resume();
          } catch (error) {
            fail(error);
            return;
          }
          finishIfReady();
        },
        (error: unknown) => {
          processing -= 1;
          fail(error);
        },
      );
    });
    stream.on("error", fail);
    stream.on("end", () => {
      ended = true;
      finishIfReady();
    });
    stream.on("status", (value: StatusObject) => {
      statusObject = value;
      finishIfReady();
    });
  });
}
