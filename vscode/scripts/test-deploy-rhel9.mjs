import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const script = fileURLToPath(new URL("deploy-rhel9.sh", import.meta.url));
const python =
  process.env.CTK_PYTHON ?? resolve(dirname(script), "../../.venv/bin/python");

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), "ctk-deploy-check-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const repo = join(root, "checkout");
  const prefix = join(root, 'installed space % $value "quote"');
  const library = join(root, "helpers");
  const config = join(root, "config");
  const log = join(root, "calls");
  const vsix = join(root, "prototype.vsix");
  const code = join(root, "code cli");
  const packageJson = {
    publisher: "clang-toolkit",
    name: "clang-toolkit-prototype",
    version: "0.2.36",
    packageManager: "pnpm@10.15.1",
  };
  for (const folder of [
    "vscode/examples",
    "vscode/scripts",
    "skills/ctk-script/scripts",
    "scripts",
  ])
    mkdirSync(join(repo, folder), { recursive: true });
  writeFileSync(join(repo, "vscode/package.json"), JSON.stringify(packageJson));
  writeFileSync(join(repo, "uv.lock"), "");
  copyFileSync(
    join(dirname(script), "user-settings.py"),
    join(repo, "vscode/scripts/user-settings.py"),
  );
  writeFileSync(
    join(repo, "skills/ctk-script/scripts/ctk_helpers.ctk"),
    "bundled",
  );
  for (const example of [
    "semantic-inspector.cpp",
    "actions-demo.cpp",
    "order-fields.ctk-action",
  ])
    writeFileSync(join(repo, "vscode/examples", example), example);
  writeFileSync(
    join(repo, "scripts/build-rhel9.sh"),
    '#!/usr/bin/env bash\nprintf "build:%s\\n" "$SKIP_TESTS" >> "$CTK_DEPLOY_LOG"\nmkdir -p "$BUILD_DIR/server"\nfor name in ctk-server ctk-index-worker; do printf "#!/bin/sh\\nexit 0\\n" > "$BUILD_DIR/server/$name"; done\n',
  );
  const zipped = spawnSync(
    python,
    [
      "-c",
      "import sys,zipfile; z=zipfile.ZipFile(sys.argv[1],'w'); z.write(sys.argv[2],'extension/package.json'); z.writestr('extension/console/worker.py','probe'); z.close()",
      vsix,
      join(repo, "vscode/package.json"),
    ],
    { encoding: "utf8" },
  );
  assert.equal(zipped.status, 0, zipped.stderr);
  writeFileSync(
    code,
    `#!/usr/bin/env bash
printf 'code:%s\\n' "$*" >> "$CTK_DEPLOY_LOG"
case "$*" in
  *--version*) printf '1.140.0\\nrevision\\nx64\\n' ;;
  *--list-extensions*) printf 'clang-toolkit.clang-toolkit-prototype@%s\\n' "\${CTK_DEPLOY_INSTALLED_VERSION:-0.2.36}" ;;
esac
`,
  );
  chmodSync(code, 0o755);
  const env = {
    ...process.env,
    CTK_DEPLOY_LOG: log,
    CTK_DEPLOY_PYTHON: python,
    XDG_CONFIG_HOME: config,
    XDG_RUNTIME_DIR: root,
    VSCODE_AGENT_FOLDER: "",
    VSCODE_PORTABLE: "",
  };
  const args = [
    "--repo",
    repo,
    "--prefix",
    prefix,
    "--library-directory",
    library,
    "--code",
    code,
    "--vsix",
    vsix,
    "--skip-deps",
  ];
  const harness = `
source "$1"
shift
check_platform() { :; }
flock() { :; }
ldd() { printf 'statically linked test stub\\n'; }
uv() {
  printf 'uv:%s\\n' "$*" >> "$CTK_DEPLOY_LOG"
  mkdir -p "$UV_PROJECT_ENVIRONMENT/bin"
  printf '#!/usr/bin/env bash\\nexec %q "$@"\\n' "$CTK_DEPLOY_PYTHON" > "$UV_PROJECT_ENVIRONMENT/bin/python"
  chmod +x "$UV_PROJECT_ENVIRONMENT/bin/python"
}
systemctl() { printf 'systemctl:%s\\n' "$*" >> "$CTK_DEPLOY_LOG"; }
smoke_test() { printf 'smoke:%s\\n' "$endpoint" >> "$CTK_DEPLOY_LOG"; }
main "$@"
`;
  const run = (extra = [], overrides = {}) =>
    spawnSync("bash", ["-c", harness, "check", script, ...args, ...extra], {
      env: { ...env, ...overrides },
      encoding: "utf8",
      timeout: 30000,
    });
  return {
    root,
    repo,
    prefix,
    library,
    config,
    log,
    vsix,
    code,
    env,
    args,
    run,
  };
}

test("help and dry-run do not create the deployment or launch commands", (t) => {
  const f = fixture(t);
  for (const option of ["--help", "--dry-run"]) {
    const result = spawnSync("bash", [script, ...f.args, option], {
      env: f.env,
      encoding: "utf8",
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(existsSync(f.prefix), false);
    assert.equal(existsSync(f.log), false);
  }
});

test("rejects incomplete options and invalid server addresses before writing", (t) => {
  const f = fixture(t);
  for (const extra of [
    ["--workspace", "--dry-run"],
    ["--settings-file", "--dry-run"],
    ["--demo", "--workspace", f.root],
    ["--unknown"],
    ["--server", "remote.example:5000"],
    ["--server", "localhost:0"],
    ["--server", "localhost:65536"],
    ["--server", "unix:///"],
  ]) {
    const result = f.run(extra);
    assert.notEqual(result.status, 0);
    assert.equal(existsSync(f.prefix), false);
    assert.equal(existsSync(f.log), false);
  }
});

test("deploys an existing server, preserves helpers/settings, and reruns from its installed VSIX", (t) => {
  const f = fixture(t);
  mkdirSync(f.library);
  writeFileSync(join(f.library, "ctk_helpers.ctk"), "user helper");
  const workspace = join(f.root, "project");
  mkdirSync(join(workspace, ".vscode"), { recursive: true });
  const settings = join(workspace, ".vscode/settings.json");
  writeFileSync(settings, '{"editor.fontSize":17}');
  const userSettings = join(
    f.config,
    "Code/User/profiles/testing/settings.json",
  );
  mkdirSync(dirname(userSettings), { recursive: true });
  mkdirSync(join(f.config, "Code/User/globalStorage"), { recursive: true });
  writeFileSync(
    join(f.config, "Code/User/globalStorage/storage.json"),
    JSON.stringify({
      userDataProfiles: [{ name: "Testing Profile", location: "testing" }],
    }),
  );
  const original =
    '{\n  // Keep my editor settings\n  "editor.fontSize": 17,\n  "ctk.server": "old",\n  "nested": {"ctk.server": "keep nested",},\n}\n';
  writeFileSync(userSettings, original);
  const extra = [
    "--server",
    "127.0.0.1:12345",
    "--workspace",
    workspace,
    "--profile",
    "Testing Profile",
  ];
  for (let attempt = 0; attempt < 2; attempt++) {
    const result = f.run([
      ...extra,
      "--vsix",
      attempt === 0 ? f.vsix : join(f.prefix, "clang-toolkit-prototype.vsix"),
    ]);
    assert.equal(result.status, 0, result.stderr || result.stdout);
  }
  const calls = readFileSync(f.log, "utf8");
  assert.doesNotMatch(calls, /build:|systemctl:/);
  assert.match(calls, /code:--profile Testing Profile --install-extension/);
  assert.match(calls, /smoke:127.0.0.1:12345/);
  assert.equal(
    readFileSync(join(f.library, "ctk_helpers.ctk"), "utf8"),
    "user helper",
  );
  assert.equal(readFileSync(settings, "utf8"), '{"editor.fontSize":17}');
  const generated = JSON.parse(
    readFileSync(join(f.prefix, "ctk.code-workspace")),
  );
  assert.equal(generated.folders[0].path, workspace);
  assert.equal(generated.settings, undefined);
  const user = readFileSync(userSettings, "utf8");
  assert.match(user, /\/\/ Keep my editor settings/);
  assert.match(user, /"editor.fontSize": 17/);
  assert.match(user, /"nested": \{"ctk.server": "keep nested",\}/);
  assert.ok(
    user.includes(JSON.stringify(join(f.prefix, "runtime/bin/python"))),
  );
  assert.ok(user.includes(JSON.stringify(f.library)));
  assert.match(user, /"ctk.server": "127.0.0.1:12345"/);
  assert.equal(readFileSync(`${userSettings}.ctk-backup`, "utf8"), original);
  assert.equal(
    readFileSync(join(f.prefix, "console/worker.py"), "utf8"),
    "probe",
  );
  assert.equal(existsSync(join(f.prefix, "vsix.sha256")), true);
});

test("installs for the user without requiring or creating a workspace", (t) => {
  const f = fixture(t);
  const result = f.run(["--full-tests"]);
  assert.equal(result.status, 0, result.stderr || result.stdout);
  const calls = readFileSync(f.log, "utf8");
  assert.match(calls, /build:0/);
  assert.match(calls, /systemctl:--user restart ctk-vscode-prototype.service/);
  const unit = join(f.config, "systemd/user/ctk-vscode-prototype.service");
  const text = readFileSync(unit, "utf8");
  assert.match(
    text,
    /installed space %% \$\$value \\"quote\\"\/bin\/ctk-server"/,
  );
  assert.match(text, /Environment="CTK_STORAGE_ROOT=.*%% \$value/);
  assert.equal(existsSync(join(f.prefix, "bin/ctk-index-worker")), true);
  assert.equal(
    readFileSync(join(f.library, "ctk_helpers.ctk"), "utf8"),
    "bundled",
  );
  const user = JSON.parse(
    readFileSync(join(f.config, "Code/User/settings.json"), "utf8"),
  );
  assert.equal(user["ctk.server"], `unix://${f.root}/ctk-vscode/ctk.sock`);
  assert.equal(user["ctk.pythonPath"], join(f.prefix, "runtime/bin/python"));
  assert.equal(user["ctk.libraryDirectory"], f.library);
  assert.equal(existsSync(join(f.prefix, "ctk.code-workspace")), false);
  assert.equal(existsSync(join(f.prefix, "demo")), false);
  assert.match(result.stdout, /Open any trusted C\+\+ project/);
  // A previous local deployment must not make --server restart that service.
  const reuse = f.run(["--server", `unix://${f.root}/ctk-vscode/ctk.sock`]);
  assert.equal(reuse.status, 0, reuse.stderr);
  assert.equal(
    (readFileSync(f.log, "utf8").match(/systemctl:--user restart/g) ?? [])
      .length,
    1,
  );
});

test("creates a demo only when requested and migrates old shortcut settings", (t) => {
  const f = fixture(t);
  const result = f.run(["--demo", "--server", "localhost:12345"]);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(existsSync(join(f.prefix, "demo/actions-demo.cpp")), true);
  assert.equal(
    existsSync(join(f.prefix, "demo/.ctk/actions/order-fields.ctk-action")),
    true,
  );
  const shortcut = join(f.prefix, "ctk.code-workspace");
  writeFileSync(
    shortcut,
    JSON.stringify({
      folders: [{ path: "old project" }],
      settings: {
        "ctk.server": "old",
        "ctk.pythonPath": "old",
        "editor.fontSize": 17,
      },
    }),
  );
  const reuse = f.run(["--server", "localhost:12345"]);
  assert.equal(reuse.status, 0, reuse.stderr);
  assert.deepEqual(JSON.parse(readFileSync(shortcut, "utf8")), {
    folders: [{ path: "old project" }],
    settings: { "editor.fontSize": 17 },
  });
});

test("Remote-SSH installs configure host user settings across projects", (t) => {
  const f = fixture(t);
  const agent = join(f.root, "remote-agent");
  const settings = join(agent, "data/Machine/settings.json");
  mkdirSync(dirname(settings), { recursive: true });
  writeFileSync(settings, '{"files.autoSave":"afterDelay"}');
  const result = f.run(["--server", "localhost:12345"], {
    VSCODE_AGENT_FOLDER: agent,
  });
  assert.equal(result.status, 0, result.stderr);
  const user = JSON.parse(readFileSync(settings, "utf8"));
  assert.equal(user["ctk.server"], "localhost:12345");
  assert.equal(user["files.autoSave"], "afterDelay");
  assert.equal(existsSync(join(f.config, "Code/User/settings.json")), false);
  assert.equal(existsSync(join(f.prefix, "ctk.code-workspace")), false);
});

test("profiles inheriting default settings keep comment-only user settings", (t) => {
  const f = fixture(t);
  const user = join(f.config, "Code/User");
  mkdirSync(join(user, "globalStorage"), { recursive: true });
  writeFileSync(join(user, "settings.json"), "// Personal preferences");
  writeFileSync(
    join(user, "globalStorage/storage.json"),
    JSON.stringify({
      userDataProfiles: [
        {
          name: "Inherited",
          location: "inherited",
          useDefaultFlags: { settings: true },
        },
      ],
    }),
  );
  const result = f.run([
    "--server",
    "localhost:12345",
    "--profile",
    "Inherited",
  ]);
  assert.equal(result.status, 0, result.stderr);
  const settings = readFileSync(join(user, "settings.json"), "utf8");
  assert.match(settings, /\/\/ Personal preferences\n/);
  assert.match(settings, /"ctk.server": "localhost:12345"/);
  assert.equal(
    existsSync(join(user, "profiles/inherited/settings.json")),
    false,
  );
});

test("detects remote CLI settings without a Remote-SSH environment variable", (t) => {
  const f = fixture(t);
  const remote = join(
    f.root,
    ".vscode-server/cli/servers/Stable-test/server/bin/code-server",
  );
  mkdirSync(dirname(remote), { recursive: true });
  copyFileSync(f.code, remote);
  const result = f.run(["--server", "localhost:12345", "--code", remote]);
  assert.equal(result.status, 0, result.stderr);
  const user = JSON.parse(
    readFileSync(
      join(f.root, ".vscode-server/data/Machine/settings.json"),
      "utf8",
    ),
  );
  assert.equal(user["ctk.server"], "localhost:12345");
});

test("custom user settings preserve JSONC, CRLF, symlinks and reject malformed files", (t) => {
  const f = fixture(t);
  const target = join(f.root, "custom-settings.json");
  const link = join(f.root, "linked-settings.json");
  const original =
    '{\r\n/* my settings */\r\n"ctk.server": ["incorrect type", {"nested":true}],\r\n"editor.rulers": [80, 120,], // keep trailing comment\r\n}\r\n';
  writeFileSync(target, original);
  symlinkSync(target, link);
  const result = f.run([
    "--server",
    "localhost:12345",
    "--settings-file",
    link,
  ]);
  assert.equal(result.status, 0, result.stderr);
  const updated = readFileSync(target, "utf8");
  assert.match(updated, /\/\* my settings \*\//);
  assert.match(updated, /"ctk.server": "localhost:12345"/);
  assert.match(
    updated,
    /"editor.rulers": \[80, 120,\], \/\/ keep trailing comment\r\n/,
  );
  assert.equal(updated.replaceAll("\r\n", "").includes("\n"), false);
  assert.equal(readFileSync(`${target}.ctk-backup`, "utf8"), original);
  const invalid = '{"editor.fontSize": 18, incomplete';
  writeFileSync(target, invalid);
  const failed = f.run([
    "--server",
    "localhost:12345",
    "--settings-file",
    link,
  ]);
  assert.notEqual(failed.status, 0);
  assert.match(failed.stderr, /Cannot configure CTK user settings/);
  assert.equal(readFileSync(target, "utf8"), invalid);
  assert.equal(readFileSync(`${target}.ctk-backup`, "utf8"), original);
});

test("reuses its installed Node runtime when system Node is absent", (t) => {
  const f = fixture(t);
  const privateBin = join(f.prefix, "tools/node-v22.23.3-linux-x64/bin");
  mkdirSync(privateBin, { recursive: true });
  symlinkSync(process.execPath, join(privateBin, "node"));
  writeFileSync(join(privateBin, "npm"), "#!/bin/sh\nexit 0\n");
  chmodSync(join(privateBin, "npm"), 0o755);
  const noSystemNode = join(f.root, "empty-path");
  mkdirSync(noSystemNode);
  const result = spawnSync(
    "bash",
    [
      "-c",
      'source "$1"; deploy_dir="$2"; skip_deps=1; PATH="$3"; ensure_node; command -v node',
      "check",
      script,
      f.prefix,
      noSystemNode,
    ],
    { encoding: "utf8" },
  );
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), join(privateBin, "node"));
});

test("rejects foreign services and unmanaged directories before building", (t) => {
  const f = fixture(t);
  const unit = join(f.config, "systemd/user/ctk-vscode-prototype.service");
  mkdirSync(dirname(unit), { recursive: true });
  writeFileSync(unit, "[Service]\nExecStart=/custom/server\n");
  const result = f.run();
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /not managed/);
  assert.equal(existsSync(f.prefix), false);
  mkdirSync(f.prefix);
  writeFileSync(join(f.prefix, "personal.txt"), "keep");
  const foreign = f.run(["--server", "localhost:12345"]);
  assert.notEqual(foreign.status, 0);
  assert.match(foreign.stderr, /not managed/);
  assert.equal(existsSync(f.log), false);
});

test("fails on an incompatible VSIX and on a failed installed-version check", (t) => {
  const f = fixture(t);
  const packagePath = join(f.repo, "vscode/package.json");
  const original = readFileSync(packagePath, "utf8");
  writeFileSync(packagePath, original.replace("0.2.36", "0.2.99"));
  const result = f.run(["--server", "localhost:12345"]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /identity\/version/);
  assert.doesNotMatch(readFileSync(f.log, "utf8"), /--install-extension/);
  writeFileSync(packagePath, original);
  const incorrect = f.run(["--server", "localhost:12345"], {
    CTK_DEPLOY_INSTALLED_VERSION: "0.2.1",
  });
  assert.notEqual(
    incorrect.status,
    0,
    incorrect.stdout + readFileSync(f.log, "utf8"),
  );
  assert.match(incorrect.stderr, /expected installed extension version/);
});

test("builds with pinned pnpm and stops packaging when an extension check fails", (t) => {
  const f = fixture(t);
  const template = join(f.root, "pnpm-stub");
  writeFileSync(
    template,
    '#!/usr/bin/env bash\nprintf "pnpm:%s\\n" "$*" >> "$CTK_DEPLOY_LOG"\nif [[ "$*" == *" test" ]]; then\n  [[ -x "$CTK_PYTHON" ]] || exit 8\n  printf "python:%s\\n" "$CTK_PYTHON" >> "$CTK_DEPLOY_LOG"\n  if [[ "$CTK_DEPLOY_FAIL_TEST" == 1 ]]; then exit 9; fi\nfi\nif [[ "$*" == *" package" ]]; then [[ "$(command -v pnpm)" == "$0" ]] || exit 7; fi\n',
  );
  const harness = `
source "$1"
repo_root="$2"
deploy_dir="$3"
python_binary="$CTK_DEPLOY_PYTHON"
ensure_node() { :; }
npm() {
  printf 'npm:%s\\n' "$*" >> "$CTK_DEPLOY_LOG"
  mkdir -p "$deploy_dir/tools/pnpm/node_modules/.bin"
  cp "$CTK_DEPLOY_PNPM_STUB" "$deploy_dir/tools/pnpm/node_modules/.bin/pnpm"
  chmod +x "$deploy_dir/tools/pnpm/node_modules/.bin/pnpm"
}
build_extension
`;
  for (const failTests of ["0", "1"]) {
    rmSync(f.log, { force: true });
    const result = spawnSync(
      "bash",
      ["-c", harness, "check", script, f.repo, f.prefix],
      {
        env: {
          ...f.env,
          CTK_DEPLOY_PNPM_STUB: template,
          CTK_DEPLOY_FAIL_TEST: failTests,
        },
        encoding: "utf8",
      },
    );
    const calls = readFileSync(f.log, "utf8");
    assert.match(calls, /npm:install .*pnpm@10\.15\.1/);
    assert.match(calls, /pnpm:--dir .*typescript install --frozen-lockfile/);
    assert.match(calls, /pnpm:--dir .*vscode install --frozen-lockfile/);
    assert.match(
      calls,
      /pnpm:--dir .*vscode check\npnpm:--dir .*vscode lint\npnpm:--dir .*vscode test\n/,
    );
    assert.ok(calls.includes(`python:${python}\n`));
    if (failTests === "1") {
      assert.equal(result.status, 9, result.stderr);
      assert.doesNotMatch(calls, /vscode package/);
    } else {
      assert.equal(result.status, 0, result.stderr);
      assert.match(calls, /vscode package/);
    }
  }
});
