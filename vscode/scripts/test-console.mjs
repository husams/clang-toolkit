import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const python =
  process.env.CTK_PYTHON ??
  resolve(
    process.platform === "win32"
      ? "../.venv/Scripts/python.exe"
      : "../.venv/bin/python",
  );
const result = spawnSync(
  python,
  [
    "-B",
    "-m",
    "unittest",
    "discover",
    "-s",
    "tests",
    "-p",
    "test_editor_service.py",
  ],
  { stdio: "inherit" },
);
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
