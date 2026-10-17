import { cp, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { startTestProcess, stopTestProcess } from "./test-process.mjs";

const directory = await mkdtemp(resolve(tmpdir(), "ctk-host-")),
  workspace = resolve(directory, "workspace");
const children = [];
let cleaning;
let stopping = false;
function cleanup() {
  cleaning ??= (async () => {
    const results = await Promise.allSettled(children.map(stopTestProcess));
    const errors = results.filter((result) => result.status === "rejected");
    if (errors.length)
      throw new AggregateError(
        errors.map((result) => result.reason),
        "Could not close all test processes",
      );
    await rm(directory, { recursive: true, force: true });
    console.log("CTK_TEST_PROCESSES_CLOSED");
  })();
  return cleaning;
}
const interrupt = (code) => {
  stopping = true;
  void cleanup().then(
    () => process.exit(code),
    (error) => {
      console.error(error);
      process.exit(1);
    },
  );
};
const interrupted = () => interrupt(130);
const terminated = () => interrupt(143);
process.once("SIGINT", interrupted);
process.once("SIGTERM", terminated);
try {
  await mkdir(resolve(workspace, ".vscode"), { recursive: true });
  await cp("examples/demo.cpp", resolve(workspace, "demo.cpp"));
  await cp(
    "examples/find-functions.ctk",
    resolve(workspace, "find-functions.ctk"),
  );
  const socket = resolve(directory, "ctk.sock"),
    config = resolve(directory, "server.yaml");
  await writeFile(
    config,
    `network:\n  transport: unix\n  unix:\n    socket_path: ${socket}\n`,
  );
  await writeFile(
    resolve(workspace, ".vscode/settings.json"),
    JSON.stringify({
      "ctk.server": `unix://${socket}`,
      "ctk.compileArguments": ["-std=c++20"],
      "ctk.pythonPath":
        process.env.CTK_PYTHON ?? resolve("../.venv/bin/python"),
      ...(process.env.CTK_TEST_DEFAULT_LIBRARY === "1"
        ? {}
        : { "ctk.libraryDirectory": resolve("../skills/ctk-script/scripts") }),
    }),
  );
  if (stopping) throw new Error("Test run interrupted before launch");
  const server = startTestProcess(
    process.env.CTK_SERVER ?? resolve("../build/dev/server/ctk-server"),
    ["-c", config],
    {
      env: { ...process.env, CTK_STORAGE_ROOT: resolve(directory, "storage") },
      stdio: "ignore",
    },
  );
  children.push(server);
  const vscode = startTestProcess(
    process.env.VSCODE_EXECUTABLE_PATH ??
      "/Applications/Visual Studio Code.app/Contents/MacOS/Code",
    [
      workspace,
      "--new-window",
      "--disable-extensions",
      "--disable-workspace-trust",
      "--skip-welcome",
      "--skip-release-notes",
      "--user-data-dir",
      resolve(directory, "profile"),
      "--extensions-dir",
      resolve(directory, "extensions"),
      "--disable-updates",
      `--extensionDevelopmentPath=${resolve(".")}`,
      `--extensionTestsPath=${resolve("dist/extension-tests.cjs")}`,
    ],
  );
  children.push(vscode);
  const deadline = setTimeout(
    () => {
      console.error(
        "VS Code extension tests exceeded ten minutes; closing the test window.",
      );
      interrupt(1);
    },
    10 * 60 * 1000,
  );
  try {
    const result = await vscode.exited;
    if (result.error) throw result.error;
    if (result.code !== 0)
      throw new Error(
        `VS Code extension tests failed (${result.code ?? result.signal})`,
      );
  } finally {
    clearTimeout(deadline);
  }
} finally {
  await cleanup();
  process.removeListener("SIGINT", interrupted);
  process.removeListener("SIGTERM", terminated);
}
