import { execFile, spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { promisify } from "node:util";

const execute = promisify(execFile);
const closing = new WeakMap();

/** Each disposable test process owns a separate POSIX process group. */
export function startTestProcess(executable, args, options = {}) {
  const child = spawn(executable, args, {
    stdio: "inherit",
    ...options,
    detached: process.platform !== "win32",
  });
  const exited = new Promise((resolve) => {
    child.once("error", (error) => resolve({ error }));
    child.once("exit", (code, signal) => resolve({ code, signal }));
  });
  return { child, exited };
}

async function groupExists(pid) {
  try {
    process.kill(-pid, 0);
    return true;
  } catch (error) {
    if (error.code === "ESRCH") return false;
    if (error.code === "EPERM") {
      // Some macOS process groups report EPERM during teardown. Confirm
      // membership instead of treating a permission check as a live process.
      const { stdout } = await execute("ps", ["-axo", "pgid="]);
      return stdout.split(/\s+/).includes(String(pid));
    }
    throw error;
  }
}

async function stop(handle) {
  const { child } = handle;
  if (!child.pid) return;
  if (process.platform === "win32") {
    if (child.exitCode === null && child.signalCode === null) {
      try {
        await execute("taskkill", ["/PID", String(child.pid), "/T", "/F"]);
      } catch (error) {
        if (child.exitCode === null && child.signalCode === null) throw error;
      }
    }
  } else {
    const signal = async (name) => {
      try {
        process.kill(-child.pid, name);
      } catch (error) {
        if (error.code === "ESRCH") return;
        if (error.code === "EPERM" && !(await groupExists(child.pid))) return;
        throw error;
      }
    };
    await signal("SIGTERM");
    const graceful = Date.now() + 1000;
    while ((await groupExists(child.pid)) && Date.now() < graceful)
      await delay(25);
    if (await groupExists(child.pid)) await signal("SIGKILL");
    const forced = Date.now() + 2000;
    while ((await groupExists(child.pid)) && Date.now() < forced)
      await delay(25);
    if (await groupExists(child.pid))
      throw new Error(`Test process group ${child.pid} did not close`);
  }
  await handle.exited;
}

/** Also closes descendants left behind after their launcher has exited. */
export function stopTestProcess(handle) {
  let pending = closing.get(handle);
  if (!pending) {
    pending = stop(handle);
    closing.set(handle, pending);
  }
  return pending;
}
