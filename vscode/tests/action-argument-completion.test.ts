import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { pathArgumentSuggestions } from "../src/action-argument-completion.js";
import { parseNodeAction } from "../src/actions.js";

describe("Options argument completion", () => {
  const directories: string[] = [];
  afterEach(async () => {
    for (const directory of directories.splice(0))
      await rm(directory, { recursive: true, force: true });
  });
  it("completes literal paths, folders and nested files without quotes or executing text", async () => {
    const directory = await mkdtemp(resolve(tmpdir(), "ctk-options-"));
    directories.push(directory);
    await mkdir(resolve(directory, "source dir"));
    await writeFile(
      resolve(directory, "source dir", "nested 'file'.cpp"),
      "int value;",
    );
    await writeFile(resolve(directory, "source file.cpp"), "int value;");
    expect(
      (await pathArgumentSuggestions("sou", directory)).map(
        (item) => item.text,
      ),
    ).toEqual(["source dir/", "source file.cpp"]);
    expect(
      (await pathArgumentSuggestions("sou", directory, true)).map(
        (item) => item.text,
      ),
    ).toEqual(["source dir/"]);
    const [nested] = await pathArgumentSuggestions("source dir/", directory);
    expect(nested?.text).toBe("source dir/nested 'file'.cpp");
    expect(nested?.kind).toBe("file");
    expect(
      (await pathArgumentSuggestions(`${directory}/sou`, directory))[0]?.text,
    ).toBe(`${directory}/source dir/`);
    expect(await pathArgumentSuggestions("missing/", directory)).toEqual([]);
    expect(await pathArgumentSuggestions("bad\0", directory)).toEqual([]);
    expect((await pathArgumentSuggestions("~", directory))[0]?.text).toBe("~/");
  });
  it("validates optional completion hints without changing the CTK callable parameters", () => {
    const source =
      "---\nname: inspect\ndescription: Inspect\narguments:\n  - name: wanted\n    description: Class name\n    completion: class\n---\nmatch cxxRecordDecl(hasName(wanted)) in node";
    const action = parseNodeAction("test.ctk-action", source);
    expect(action.arguments[0]?.completion).toBe("class");
    expect(action.generated).toContain("inspect(node, wanted)");
    expect(() =>
      parseNodeAction(
        "bad",
        source.replace(
          "completion: class",
          "completion: class\n    type: number",
        ),
      ),
    ).toThrow("Autocomplete requires a string");
    expect(() =>
      parseNodeAction(
        "bad",
        source.replace("completion: class", "completion: code"),
      ),
    ).toThrow();
  });
});
