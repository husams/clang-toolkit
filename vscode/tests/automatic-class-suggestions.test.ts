import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AutomaticClassSuggestions } from "../src/automatic-class-suggestions.js";

describe("automatic class-name popup", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("shows once for the latest typed prefix, without a completion shortcut", async () => {
    let draft = { key: "script:1:1", value: "d" };
    const context = vi.fn(async () => true),
      show = vi.fn(async () => {});
    const trigger = new AutomaticClassSuggestions(
      () => draft,
      context,
      show,
      vi.fn(),
    );
    trigger.changed();
    draft = { key: "script:2:2", value: "de" };
    trigger.changed();
    draft = { key: "script:3:3", value: "demo::Or" };
    trigger.changed();
    // VS Code can deliver the cursor update after the document change event.
    draft = { ...draft, key: "script:3:11" };
    await vi.advanceTimersByTimeAsync(180);
    expect(context).toHaveBeenCalledExactlyOnceWith("demo::Or");
    expect(show).toHaveBeenCalledOnce();
    trigger.dispose();
  });

  it("ignores other arguments and cursor/editor changes during context lookup", async () => {
    let draft = { key: "script:1:1", value: "first argument" };
    const context = vi.fn(async () => false),
      show = vi.fn(async () => {});
    const trigger = new AutomaticClassSuggestions(
      () => draft,
      context,
      show,
      vi.fn(),
    );
    trigger.changed();
    await vi.advanceTimersByTimeAsync(180);
    expect(show).not.toHaveBeenCalled();
    context.mockImplementation(async () => {
      draft = { ...draft, key: "other editor" };
      return true;
    });
    trigger.changed();
    await vi.advanceTimersByTimeAsync(180);
    expect(show).not.toHaveBeenCalled();
    trigger.dispose();
  });

  it("drops stale in-flight requests and cancels when disabled or disposed", async () => {
    let finish: (value: boolean) => void = () => {};
    const pending = new Promise<boolean>((resolve) => {
      finish = resolve;
    });
    const show = vi.fn(async () => {});
    const trigger = new AutomaticClassSuggestions(
      () => ({ key: "same draft", value: "demo" }),
      async () => pending,
      show,
      vi.fn(),
    );
    trigger.changed();
    await vi.advanceTimersByTimeAsync(180);
    trigger.cancel();
    finish(true);
    await vi.advanceTimersByTimeAsync(0);
    expect(show).not.toHaveBeenCalled();
    trigger.changed();
    trigger.dispose();
    await vi.advanceTimersByTimeAsync(180);
    expect(show).not.toHaveBeenCalled();
  });
});
