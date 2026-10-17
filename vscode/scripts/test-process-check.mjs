import assert from "node:assert/strict";
import {
  chmod,
  mkdtemp,
  readFile,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { setTimeout as delay } from "node:timers/promises";
import { startTestProcess, stopTestProcess } from "./test-process.mjs";

function exists(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    if (error.code === "ESRCH") return false;
    throw error;
  }
}
for (const code of [0, 1]) {
  test(`closes descendants after their launcher exits ${code}`, {
    skip: process.platform === "win32",
  }, async () => {
    const folder = await mkdtemp(join(tmpdir(), "ctk-process-check-"));
    const marker = join(folder, "child.pid");
    const handle = startTestProcess(
      process.execPath,
      [
        "-e",
        `
      const {spawn}=require('node:child_process');
      const {writeFileSync}=require('node:fs');
      const child=spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{stdio:'ignore'});
      writeFileSync(process.argv[1],String(child.pid));
      process.exit(${code});
    `,
        marker,
      ],
      { stdio: "ignore" },
    );
    try {
      assert.equal((await handle.exited).code, code);
      const pid = Number(await readFile(marker, "utf8"));
      assert.equal(exists(pid), true);
      await stopTestProcess(handle);
      assert.equal(exists(pid), false);
      await stopTestProcess(handle);
    } finally {
      await stopTestProcess(handle);
      await rm(folder, { recursive: true, force: true });
    }
  });
}
test("forces a test process to close when it ignores graceful shutdown", {
  skip: process.platform === "win32",
}, async () => {
  const folder = await mkdtemp(join(tmpdir(), "ctk-process-check-"));
  const marker = join(folder, "ready");
  const handle = startTestProcess(
    process.execPath,
    [
      "-e",
      `
    process.on('SIGTERM',()=>{});
    require('node:fs').writeFileSync(process.argv[1],'ready');
    setInterval(()=>{},1000);
  `,
      marker,
    ],
    { stdio: "ignore" },
  );
  try {
    const deadline = Date.now() + 5000;
    while (
      !(await readFile(marker).catch((error) => {
        if (error.code !== "ENOENT") throw error;
        return undefined;
      })) &&
      Date.now() < deadline
    )
      await delay(10);
    assert.ok(await readFile(marker));
    await stopTestProcess(handle);
    assert.equal((await handle.exited).signal, "SIGKILL");
    assert.equal(exists(handle.child.pid), false);
  } finally {
    await stopTestProcess(handle);
    await rm(folder, { recursive: true, force: true });
  }
});
test("reports a failed launch without leaving a process", async () => {
  const handle = startTestProcess(
    join(tmpdir(), "missing-ctk-test-executable"),
    [],
    { stdio: "ignore" },
  );
  assert.equal((await handle.exited).error.code, "ENOENT");
  await stopTestProcess(handle);
});

test("checks actual group membership when macOS denies a liveness probe", {
  skip: process.platform === "win32",
}, async (context) => {
  const handle = startTestProcess(process.execPath, ["-e", "process.exit(0)"], {
    stdio: "ignore",
  });
  await handle.exited;
  const kill = process.kill.bind(process);
  context.mock.method(process, "kill", (pid, signal) => {
    if (pid === -handle.child.pid && signal === 0)
      throw Object.assign(new Error("kill EPERM"), { code: "EPERM" });
    return kill(pid, signal);
  });
  await stopTestProcess(handle);
});

test("interrupted host runs close their window, descendants and server", {
  skip: process.platform === "win32",
}, async () => {
  const folder = await mkdtemp(join(tmpdir(), "ctk-harness-check-"));
  const fake = join(folder, "fake-code.cjs"),
    marker = join(folder, "window.json");
  await writeFile(
    fake,
    `#!/usr/bin/env node
    const {writeFileSync}=require('node:fs');
    if(process.argv.includes('--new-window')) {
      const child=require('node:child_process').spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{stdio:'ignore'});
      writeFileSync(process.env.CTK_CLEANUP_PROBE,JSON.stringify({pid:process.pid,child:child.pid,workspace:process.argv[2]}));
    } else {
      writeFileSync(process.env.CTK_CLEANUP_PROBE+'.server',String(process.pid));
    }
    setInterval(()=>{},1000);
  `,
  );
  await chmod(fake, 0o755);
  const handle = startTestProcess(
    process.execPath,
    [resolve("scripts/test-host.mjs")],
    {
      stdio: "ignore",
      env: {
        ...process.env,
        VSCODE_EXECUTABLE_PATH: fake,
        CTK_SERVER: fake,
        CTK_CLEANUP_PROBE: marker,
      },
    },
  );
  try {
    const deadline = Date.now() + 5000;
    let content;
    while (!content && Date.now() < deadline) {
      content = await readFile(marker, "utf8").catch((error) => {
        if (error.code !== "ENOENT") throw error;
        return undefined;
      });
      if (!content) await delay(10);
    }
    assert.ok(content, "the disposable window must have started");
    const window = JSON.parse(content);
    const server = Number(await readFile(`${marker}.server`, "utf8"));
    process.kill(handle.child.pid, "SIGTERM");
    assert.equal((await handle.exited).code, 143);
    for (const pid of [window.pid, window.child, server])
      assert.equal(exists(pid), false);
    await assert.rejects(stat(dirname(window.workspace)), { code: "ENOENT" });
  } finally {
    await stopTestProcess(handle);
    await rm(folder, { recursive: true, force: true });
  }
});
