import workerSource from "./elk-worker-source.js";
import { GraphCanvas } from "./graph-canvas.js";
import { layoutGraph } from "./graph-layout.js";
import { GraphState } from "./graph-state.js";

const element = (tag, cls, text) => {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text) el.textContent = text;
  return el;
};
function decode(text) {
  try {
    const value = text ? JSON.parse(text) : {};
    return value && typeof value === "object" ? value : {};
  } catch (error) {
    console.warn("Ignoring invalid saved graph view", error);
    return {};
  }
}
export class GraphView {
  constructor(host, api, fullscreen = false) {
    this.host = host;
    this.api = api;
    this.fullscreen = fullscreen;
    this.cache = new Map();
    this.sequence = 0;
    new ResizeObserver(() => {
      if (this.canvas?.layout && host.clientWidth && host.clientHeight) {
        const view = this.state.view;
        if (view) this.canvas.restore(this.state.current, view);
        this.canvas.paint();
        this.status();
      } else if (this.state && host.clientWidth)
        void this.render(
          this.state.view
            ? { id: this.state.current, camera: this.state.view }
            : undefined,
        );
    }).observe(host);
  }
  update(data, override) {
    if (data?.loading) {
      this.message("Loading native graph…");
      return;
    }
    if (data?.error) {
      this.message(data.error, true);
      return;
    }
    if (!data?.model) {
      this.message(
        "Select a function or a statement inside a function, then open this view.",
      );
      return;
    }
    const model = data.model;
    if (
      this.state?.model.key === model.key &&
      !override &&
      this.canvas?.plot.isConnected
    )
      return;
    const saved = override
      ? decode(override)
      : this.api.getState()?.graphs?.[model.key];
    this.state = new GraphState(model, saved);
    this.mount();
    void this.render(
      this.state.view
        ? { id: this.state.current, camera: this.state.view }
        : undefined,
    );
  }
  message(text, retry = false) {
    this.sequence++;
    this.host.replaceChildren(element("p", "graph-message", text));
    if (retry)
      this.host.append(
        this.button("Retry", () =>
          this.api.postMessage({ type: "graph-retry" }),
        ),
      );
  }
  button(label, action, aria) {
    const b = element("button", "", label);
    b.type = "button";
    if (aria) b.setAttribute("aria-label", aria);
    b.addEventListener("click", action);
    return b;
  }
  mount() {
    const s = this.state;
    this.host.replaceChildren();
    const controls = element("div", "graph-controls");
    this.back = this.button("← Back one level", () =>
      this.navigate(s.trail.at(-2)),
    );
    controls.append(this.back);
    controls.append(
      this.button("Full graph", () => {
        s.trail = [s.model.root];
        this.canvas.fit();
        this.canvas.paint();
        this.save();
        this.breadcrumb();
      }),
    );
    controls.append(
      this.button(this.fullscreen ? "Exit fullscreen" : "Fullscreen", () =>
        this.api.postMessage(
          this.fullscreen
            ? { type: "graph-close" }
            : {
                type: "graph-fullscreen",
                key: s.model.key,
                state: JSON.stringify(s.snapshot(this.canvas.camera())),
              },
        ),
      ),
    );
    this.host.append(controls);
    this.crumb = element("nav", "graph-breadcrumb");
    this.crumb.setAttribute("aria-label", "Function breadcrumb");
    controls.insertBefore(this.crumb, controls.lastElementChild);
    const local = element("div", "graph-controls");
    if (s.model.kind === "callgraph") {
      const direction = element("select");
      direction.setAttribute("aria-label", "Call graph direction");
      for (const [value, label] of [
        ["out", "Calls from entry"],
        ["in", "Who calls this function?"],
      ]) {
        const option = element("option", "", label);
        option.value = value;
        direction.append(option);
      }
      direction.value = s.direction;
      direction.addEventListener("change", () => {
        s.cameras[`${s.direction}:${s.current}`] = this.canvas.camera();
        s.direction = direction.value;
        expand.textContent =
          s.direction === "out" ? "Expand downstream" : "Expand callers";
        s.trail = [s.model.root];
        void this.render({
          id: s.current,
          camera: s.cameras[`${s.direction}:${s.current}`],
        });
      });
      local.append(direction);
      const expand = this.button(
        s.direction === "out" ? "Expand downstream" : "Expand callers",
        () => {
          const camera = this.canvas.camera();
          s.expandAll();
          void this.render({ id: s.current, camera });
        },
      );
      local.append(expand);
      local.append(
        this.button("Collapse all", () => {
          s.expanded[s.direction].clear();
          s.trail = [s.model.root];
          void this.render();
        }),
      );
    } else local.append(element("span", "", `CFG · ${s.model.name}`));
    this.host.append(local);
    const search = element("div", "graph-search"),
      input = element("input"),
      results = element("select");
    input.type = "search";
    input.placeholder =
      s.model.kind === "cfg" ? "Find a block…" : "Find a function…";
    input.setAttribute(
      "aria-label",
      s.model.kind === "cfg"
        ? "Find a block"
        : "Find a function, including hidden calls",
    );
    results.size = 5;
    results.hidden = true;
    results.setAttribute("aria-label", "Matching graph nodes");
    let searchCamera;
    input.addEventListener("input", () => {
      searchCamera ||= this.canvas.camera();
      results.replaceChildren();
      results.hidden = !input.value;
      if (!input.value) return;
      const reachable = s.paths(false);
      for (const node of s.model.nodes)
        if (
          reachable.has(node.id) &&
          node.name.toLowerCase().includes(input.value.toLowerCase())
        ) {
          const option = element(
            "option",
            "",
            `${node.name}${node.file ? ` · ${node.file.split(/[\\/]/).at(-1)}:${node.line}` : ""}`,
          );
          option.value = node.id;
          results.append(option);
        }
      results.selectedIndex = -1;
    });
    results.addEventListener("change", () => {
      const id = results.value,
        camera = searchCamera || this.canvas.camera();
      if (!s.reveal(id)) return;
      const restored = s.visit(id, camera);
      input.value = "";
      results.hidden = true;
      searchCamera = undefined;
      void this.render(restored ? { id, camera: restored } : { frame: id });
    });
    search.append(input, results);
    local.append(search);
    this.plot = element("div", "graph-plot");
    this.plot.setAttribute("role", "group");
    this.plot.setAttribute("aria-label", "Directed graph");
    this.host.append(this.plot);
    this.canvas = new GraphCanvas(
      this.plot,
      () => {
        this.save();
        this.status();
      },
      (action, id) => {
        if (action === "drill") this.navigate(id);
        else {
          const camera = this.canvas.camera(id);
          s.toggle(id);
          void this.render({ id, camera });
        }
      },
    );
    const footer = element("div", "graph-footer");
    this.count = element("span", "graph-count");
    footer.append(this.count);
    for (const [name, x, y] of [
      ["←", 120, 0],
      ["↑", 0, 120],
      ["↓", 0, -120],
      ["→", -120, 0],
    ])
      footer.append(
        this.button(
          name,
          () => this.canvas.pan(x, y),
          `Pan ${x > 0 ? "left" : x < 0 ? "right" : y > 0 ? "up" : "down"}`,
        ),
      );
    footer.append(
      this.button("−", () => this.canvas.zoom(1 / 1.25), "Zoom out"),
    );
    this.scale = element("span");
    footer.append(
      this.scale,
      this.button("+", () => this.canvas.zoom(1.25), "Zoom in"),
      this.button("Fit graph", () => {
        this.canvas.fit();
        this.canvas.paint();
        this.save();
      }),
    );
    this.host.append(footer);
    this.notice = element(
      "div",
      "graph-warnings",
      [
        ...(!s.model.complete ? ["Native graph is partial."] : []),
        ...s.model.warnings,
      ].join(" "),
    );
    this.notice.setAttribute("role", "status");
    this.host.append(this.notice);
    this.breadcrumb();
  }
  breadcrumb() {
    const s = this.state;
    this.crumb.replaceChildren();
    this.back.disabled = s.trail.length < 2;
    for (const [i, id] of s.trail.entries()) {
      if (i) {
        const separator = element("span", "", "›");
        separator.setAttribute("aria-hidden", "true");
        this.crumb.append(separator);
      }
      const name = s.nodes.get(id).name;
      const item =
        i === s.trail.length - 1
          ? element("span", "", name)
          : this.button(
              name,
              () => this.navigate(id),
              `Return to previous view of ${name}`,
            );
      if (i === s.trail.length - 1) item.setAttribute("aria-current", "page");
      this.crumb.append(item);
    }
  }
  navigate(id) {
    if (!id || !this.canvas.layout) return;
    const same = id === this.state.current;
    const camera = this.state.visit(id, this.canvas.camera());
    this.breadcrumb();
    if (camera && !same) this.canvas.restore(id, camera);
    else this.canvas.fit(id);
    this.canvas.paint();
    this.save();
  }
  async render(restore) {
    if (!this.plot?.clientWidth || !this.plot.clientHeight) return;
    const sequence = ++this.sequence;
    const previous = { ...this.canvas.view },
      previousFunction = this.state.current;
    this.plot.setAttribute("aria-busy", "true");
    try {
      if (!this.elk) {
        const url = URL.createObjectURL(
          new Blob([workerSource], { type: "text/javascript" }),
        );
        this.elk = new globalThis.ELK({ workerUrl: url });
        window.addEventListener(
          "unload",
          () => {
            this.elk?.terminateWorker();
            URL.revokeObjectURL(url);
          },
          { once: true },
        );
      }
      const graph = this.state.visible(),
        key = JSON.stringify([
          this.state.model.key,
          graph.nodes.map((n) => n.id),
          graph.edges.map((e) => e.id),
        ]);
      let layout = this.cache.get(key);
      if (!layout) {
        layout = await layoutGraph(this.elk, this.state.model, graph);
        this.cache.set(key, layout);
        while (this.cache.size > 4)
          this.cache.delete(this.cache.keys().next().value);
      }
      if (sequence !== this.sequence) return;
      if (
        this.canvas.layout &&
        (this.state.current !== previousFunction ||
          ["x", "y", "scale"].some((k) => this.canvas.view[k] !== previous[k]))
      ) {
        const id =
            this.state.current !== previousFunction
              ? this.state.current
              : restore?.id || this.state.current,
          camera = this.canvas.camera(id);
        if (camera) restore = { id, camera };
      }
      this.canvas.set(layout, this.state);
      if (!restore?.camera || !this.canvas.restore(restore.id, restore.camera))
        this.canvas.fit(restore?.frame);
      this.canvas.paint();
      this.breadcrumb();
      this.save();
    } catch (error) {
      if (sequence === this.sequence)
        this.message(`Unable to arrange graph: ${String(error)}`, true);
    } finally {
      if (sequence === this.sequence)
        this.plot.setAttribute("aria-busy", "false");
    }
  }
  status() {
    if (!this.canvas?.layout) return;
    this.count.textContent = `${this.canvas.layout.children.length} ${this.state.model.kind === "cfg" ? "blocks" : "functions"} · ${this.canvas.visibleCount} in view`;
    this.scale.textContent = `${this.canvas.view.scale < 0.01 ? (100 * this.canvas.view.scale).toFixed(1) : Math.round(100 * this.canvas.view.scale)}%`;
  }
  save() {
    const view = this.canvas.camera();
    if (!view) return;
    this.state.view = view;
    const value = this.state.snapshot(view),
      previous = this.api.getState() || {};
    this.api.setState({
      ...previous,
      graphs: { ...previous.graphs, [this.state.model.key]: value },
    });
    if (this.fullscreen)
      this.api.postMessage({
        type: "graph-viewstate",
        state: JSON.stringify(value),
      });
    this.api.postMessage({
      type: "graph-rendered",
      key: this.state.model.key,
      nodeCount: this.canvas.layout.children.length,
      edgeCount: this.canvas.layout.edges.length,
      visibleCount: this.canvas.visibleCount,
      zoom: this.canvas.view.scale,
      labels: [...this.canvas.lines.querySelectorAll(".graph-edge-label")].map(
        (n) => n.textContent,
      ),
      trail: [...this.state.trail],
    });
    this.status();
  }
}
