import { randomUUID } from "node:crypto";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, it } from "vitest";
import { ActionService } from "../src/action-service.js";
import { parseNodeAction } from "../src/actions.js";

it("can reset and retry after the interpreter fails to start", async () => {
  const failures: string[] = [];
  const service = new ActionService(
    "missing-worker.py",
    join(tmpdir(), `missing-python-${randomUUID()}`),
    (reason) => failures.push(reason),
  );
  const action = parseNodeAction(
    "test.ctk-action",
    "---\nname: test\ndescription: Test\n---\nmatch functionDecl() in node",
  );
  const settings = {
    directory: process.cwd(),
    compileArguments: [],
    timeoutMs: 1000,
  };
  try {
    await expect(
      service.run(action, {}, ["test.cpp"], settings, 1),
    ).rejects.toThrow("ENOENT");
    await service.reset();
    await expect(
      service.run(action, {}, ["test.cpp"], settings, 1),
    ).rejects.toThrow("ENOENT");
    expect(failures).toHaveLength(2);
  } finally {
    service.dispose();
  }
});
