import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { expect, it } from "vitest";

const script = readFileSync(
  new URL("../media/pinned-query.js", import.meta.url),
  "utf8",
);

function view(state) {
  class Element {
    children = [];
    dataset = {};
    listeners = {};
    classList = { toggle() {} };
    constructor(tag) {
      this.tag = tag;
      this.expanded = false;
    }
    set open(value) {
      this.expanded = value;
      this.listeners.toggle?.();
    }
    get open() {
      return this.expanded;
    }
    addEventListener(name, callback) {
      this.listeners[name] = callback;
    }
    append(child) {
      this.children.push(child);
    }
    replaceChildren() {
      this.children = [];
    }
    setAttribute() {}
    querySelectorAll(tag) {
      return this.children.flatMap((child) => [
        ...(child.tag === tag ? [child] : []),
        ...child.querySelectorAll(tag),
      ]);
    }
  }
  const elements = Object.fromEntries(
    ["title", "query", "query-details", "count", "results"].map((id) => [
      id,
      new Element(id === "query-details" ? "details" : "div"),
    ]),
  );
  const events = {},
    frames = [];
  const api = {
    getState: () => state,
    setState: (value) => {
      state = structuredClone(value);
    },
    postMessage() {},
  };
  const window = {
    scrollY: 0,
    addEventListener: (name, callback) => {
      events[name] = callback;
    },
    scrollTo: (_x, y) => {
      window.scrollY = y;
      events.scroll?.();
    },
  };
  const document = {
    getElementById: (id) => elements[id],
    createElement: (tag) => new Element(tag),
    querySelectorAll: () => elements.results.querySelectorAll("details"),
  };
  runInNewContext(script, {
    window,
    document,
    acquireVsCodeApi: () => api,
    requestAnimationFrame: (callback) => frames.push(callback),
  });
  return {
    window,
    elements,
    state: () => state,
    initialLayout: () => events.scroll(),
    render: (snapshot) => {
      events.message({ data: { type: "snapshot", snapshot } });
      while (frames.length) frames.shift()();
    },
  };
}

const snapshot = {
  title: "Query",
  query: "varDecl()",
  fingerprints: {},
  results: [
    {
      name: "target",
      kind: "Var",
      file: "/main.cpp",
      line: 2,
      column: 1,
      excerpt: "int target;",
    },
  ],
  selected: 0,
  scroll: 240,
  expanded: ["/main.cpp"],
  queryExpanded: true,
};

it("does not overwrite saved scroll or expansion during the initial empty layout", () => {
  const panel = view(structuredClone(snapshot));
  panel.initialLayout();
  panel.render(snapshot);
  expect(panel.window.scrollY).toBe(240);
  expect(panel.elements["query-details"].open).toBe(true);
  expect(panel.state()).toMatchObject({
    scroll: 240,
    selected: 0,
    queryExpanded: true,
    expanded: ["/main.cpp"],
  });
});

it("restores validated serializer state when the webview starts without getState data", () => {
  const panel = view(undefined);
  panel.initialLayout();
  panel.render(snapshot);
  expect(panel.window.scrollY).toBe(240);
  expect(panel.elements["query-details"].open).toBe(true);
  expect(panel.state().selected).toBe(0);
});
