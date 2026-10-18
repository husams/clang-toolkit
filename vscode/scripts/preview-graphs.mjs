import { execFileSync, spawn, spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  openSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const extension = resolve(dirname(fileURLToPath(import.meta.url)), ".."),
  root = dirname(extension);
const common = dirname(
  execFileSync(
    "git",
    ["rev-parse", "--path-format=absolute", "--git-common-dir"],
    { cwd: root, encoding: "utf8" },
  ).trim(),
);
const server =
  process.env.CTK_SERVER || join(common, "build/dev/server/ctk-server");
const python =
  process.env.CTK_PYTHON ||
  join(
    existsSync(join(root, ".venv/bin/python")) ? root : common,
    ".venv/bin/python",
  );
const output = join(extension, "artifacts/graph-preview"),
  stateFile = join(output, "preview-process.json");
if (process.argv.includes("--stop")) {
  if (existsSync(stateFile)) {
    const state = JSON.parse(readFileSync(stateFile, "utf8"));
    const command =
      spawnSync("ps", ["-p", String(state.pid), "-o", "command="], {
        encoding: "utf8",
      }).stdout || "";
    if (command.includes(state.config)) process.kill(state.pid, "SIGTERM");
  }
  console.log("Graph preview server stopped.");
  process.exit(0);
}
if (!existsSync(join(extension, "dist/extension.js")))
  throw new Error("Build the extension first: pnpm build");
if (!existsSync(server) || !existsSync(python))
  throw new Error(
    "Set CTK_SERVER and CTK_PYTHON to the native server and CTK interpreter.",
  );
mkdirSync(output, { recursive: true });
const capture = spawnSync(
  python,
  [
    "-B",
    join(extension, "scripts/capture-graphs.py"),
    "--server",
    server,
    "--output",
    output,
  ],
  { stdio: "inherit" },
);
if (capture.status !== 0) process.exit(capture.status || 1);
let processInfo;
if (existsSync(stateFile)) {
  const previous = JSON.parse(readFileSync(stateFile, "utf8")),
    command =
      spawnSync("ps", ["-p", String(previous.pid), "-o", "command="], {
        encoding: "utf8",
      }).stdout || "";
  if (command.includes(previous.config)) processInfo = previous;
}
if (!processInfo) {
  const directory = mkdtempSync("/tmp/ctk-vscode-graphs-"),
    config = join(directory, "server.yaml"),
    socket = join(directory, "server.sock");
  writeFileSync(
    config,
    `network:\n  transport: unix\n  unix:\n    socket_path: ${socket}\n`,
  );
  const log = openSync(join(output, "preview-server.log"), "a"),
    child = spawn(server, ["-c", config], {
      detached: true,
      stdio: ["ignore", log, log],
      env: { ...process.env, CTK_STORAGE_ROOT: join(directory, "storage") },
    });
  child.unref();
  processInfo = { pid: child.pid, config, socket };
  writeFileSync(stateFile, JSON.stringify(processInfo));
  const end = Date.now() + 15000;
  while (!existsSync(socket)) {
    if (Date.now() > end)
      throw new Error("Preview server did not start; check preview-server.log");
    await new Promise((done) => setTimeout(done, 50));
  }
}
const workspace = join(output, "workspace");
mkdirSync(join(workspace, ".vscode"), { recursive: true });
mkdirSync(join(output, "lib"), { recursive: true });
const source = readFileSync(join(output, "orders.cpp"), "utf8");
writeFileSync(join(workspace, "orders.cpp"), source);
writeFileSync(
  join(workspace, ".vscode/settings.json"),
  JSON.stringify(
    {
      "ctk.server": `unix://${processInfo.socket}`,
      "ctk.pythonPath": python,
      "ctk.libraryDirectory": join(output, "lib"),
      "ctk.compileArguments": ["-std=c++20"],
      "workbench.startupEditor": "none",
      "extensions.ignoreRecommendations": true,
      "chat.disableAIFeatures": true,
    },
    null,
    2,
  ),
);
const line = source.slice(0, source.indexOf("int submit(")).split("\n").length;
const codeLog = openSync(join(output, "preview-code.log"), "a");
const code = spawn(
  process.env.VSCODE_EXECUTABLE_PATH ||
    (process.platform === "darwin"
      ? "/Applications/Visual Studio Code.app/Contents/MacOS/Code"
      : "code"),
  [
    "--new-window",
    "--disable-extensions",
    "--disable-workspace-trust",
    "--skip-welcome",
    "--skip-release-notes",
    "--disable-updates",
    "--user-data-dir",
    mkdtempSync(join(dirname(processInfo.config), "profile-")),
    "--extensions-dir",
    join(dirname(processInfo.config), "extensions"),
    `--extensionDevelopmentPath=${extension}`,
    "--goto",
    `${join(workspace, "orders.cpp")}:${line}:5`,
    workspace,
  ],
  { detached: true, stdio: ["ignore", codeLog, codeLog] },
);
code.on("error", (error) => {
  console.error(error.message);
  process.exitCode = 1;
});
code.unref();
await new Promise((done) => setTimeout(done, 1500));
if (code.exitCode !== null && code.exitCode !== 0)
  throw new Error(
    `VS Code did not open; check ${join(output, "preview-code.log")}`,
  );
console.log(
  "VS Code graph preview opened. Run CTK: Show Call Graph, then Expand downstream and Fit graph.",
);
