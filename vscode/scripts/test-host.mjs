import { spawn } from "node:child_process";
import { cp, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { runTests } from "@vscode/test-electron";

const directory = await mkdtemp(resolve(tmpdir(), "ctk-host-")),
  workspace = resolve(directory, "workspace");
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
    "ctk.pythonPath": process.env.CTK_PYTHON ?? resolve("../.venv/bin/python"),
    ...(process.env.CTK_TEST_DEFAULT_LIBRARY === "1"
      ? {}
      : { "ctk.libraryDirectory": resolve("../skills/ctk-script/scripts") }),
  }),
);
const server = spawn(
  process.env.CTK_SERVER ?? resolve("../build/dev/server/ctk-server"),
  ["-c", config],
  {
    env: { ...process.env, CTK_STORAGE_ROOT: resolve(directory, "storage") },
    stdio: "ignore",
  },
);
try {
  await runTests({
    vscodeExecutablePath:
      process.env.VSCODE_EXECUTABLE_PATH ??
      "/Applications/Visual Studio Code.app/Contents/MacOS/Code",
    extensionDevelopmentPath: resolve("."),
    extensionTestsPath: resolve("dist/extension-tests.cjs"),
    launchArgs: [
      workspace,
      "--disable-extensions",
      "--disable-workspace-trust",
      "--skip-welcome",
      "--skip-release-notes",
      "--user-data-dir",
      resolve(directory, "profile"),
    ],
  });
} finally {
  if (server.exitCode === null) {
    const exit = new Promise((done) => server.once("exit", done));
    server.kill();
    await exit;
  }
  await rm(directory, { recursive: true, force: true });
}
