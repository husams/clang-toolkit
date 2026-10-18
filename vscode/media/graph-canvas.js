import { bridgeCandidates, edgePath, projection } from "./graph-layout.js";

const NS = "http://www.w3.org/2000/svg";
const svg = (tag, attrs = {}) => {
  const node = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs))
    node.setAttribute(key, String(value));
  return node;
};
export class GraphCanvas {
  constructor(plot, changed, action) {
    this.plot = plot;
    this.changed = changed;
    this.action = action;
    this.view = { scale: 1, x: 0, y: 0 };
    this.lines = svg("svg", { class: "graph-lines", "aria-hidden": "true" });
    this.nodes = document.createElement("div");
    this.nodes.className = "graph-nodes";
    plot.append(this.lines, this.nodes);
    let drag,
      moved = false;
    plot.addEventListener("pointerdown", (event) => {
      moved = false;
      if (event.button !== 0 || event.target.closest("button")) return;
      moved = false;
      drag = {
        x: event.clientX,
        y: event.clientY,
        vx: this.view.x,
        vy: this.view.y,
      };
      plot.setPointerCapture(event.pointerId);
    });
    plot.addEventListener("pointermove", (event) => {
      if (!drag) return;
      moved ||=
        Math.abs(event.clientX - drag.x) + Math.abs(event.clientY - drag.y) > 4;
      this.view.x = drag.vx + event.clientX - drag.x;
      this.view.y = drag.vy + event.clientY - drag.y;
      if (!this.frame)
        this.frame = requestAnimationFrame(() => {
          this.frame = null;
          this.paint();
        });
    });
    const stop = () => {
      if (drag) {
        drag = undefined;
        this.paint();
        this.changed();
      }
    };
    plot.addEventListener("pointerup", stop);
    plot.addEventListener("pointercancel", stop);
    plot.addEventListener(
      "wheel",
      (event) => {
        event.preventDefault();
        const rect = plot.getBoundingClientRect();
        if (event.ctrlKey || event.metaKey)
          this.zoom(
            event.deltaY < 0 ? 1.15 : 1 / 1.15,
            event.clientX - rect.left,
            event.clientY - rect.top,
          );
        else {
          this.view.x -= event.deltaX;
          this.view.y -= event.deltaY;
          this.paint();
          this.changed();
        }
      },
      { passive: false },
    );
    plot.addEventListener(
      "click",
      (event) => {
        if (moved) {
          moved = false;
          event.stopPropagation();
        }
      },
      true,
    );
  }
  set(layout, state) {
    this.layout = layout;
    this.state = state;
    this.byId = new Map(layout.children.map((n) => [n.id, n]));
    this.bridges = bridgeCandidates(layout);
    this.project();
  }
  project() {
    if (this.layout)
      this.q = projection(
        this.layout,
        this.view.scale,
        this.state.model.kind === "cfg",
      );
  }
  camera(id = this.state?.current) {
    const n = this.byId?.get(id),
      p = this.plot;
    if (!n || !p.clientWidth || !p.clientHeight) return;
    return {
      scale: this.view.scale,
      ax: (this.q.x(n.x + n.width / 2) + this.view.x) / p.clientWidth,
      ay: (this.q.y(n.y + n.height / 2) + this.view.y) / p.clientHeight,
    };
  }
  restore(id, camera) {
    const n = this.byId.get(id);
    if (!n || !camera) return false;
    this.view.scale = camera.scale;
    this.project();
    this.view.x =
      camera.ax * this.plot.clientWidth - this.q.x(n.x + n.width / 2);
    this.view.y =
      camera.ay * this.plot.clientHeight - this.q.y(n.y + n.height / 2);
    return true;
  }
  fit(id) {
    const p = this.plot,
      all = id ? this.state.paths(true, id) : undefined;
    const nodes = this.layout.children.filter((n) => !all || all.has(n.id));
    const left = Math.min(...nodes.map((n) => n.x)),
      right = Math.max(...nodes.map((n) => n.x + n.width));
    const top = Math.min(...nodes.map((n) => n.y)),
      bottom = Math.max(...nodes.map((n) => n.y + n.height));
    this.view.scale = Math.max(
      id ? 0.5 : 0.005,
      Math.min(
        1,
        (p.clientHeight - 64) / Math.max(32, bottom - top),
        this.state.model.kind === "cfg"
          ? (p.clientWidth - 48) / Math.max(100, right - left)
          : 1,
      ),
    );
    this.project();
    const root = this.byId.get(id || this.state.model.root);
    const span = this.q.x(right) - this.q.x(left);
    this.view.x =
      span < p.clientWidth - 24
        ? (p.clientWidth - span) / 2 - this.q.x(left)
        : 20 - this.q.x(root.x);
    this.view.y =
      (bottom - top) * this.view.scale <= p.clientHeight - 32
        ? p.clientHeight / 2 - this.q.y((top + bottom) / 2)
        : p.clientHeight / 2 - this.q.y(root.y + root.height / 2);
  }
  zoom(factor, x = this.plot.clientWidth / 2, y = this.plot.clientHeight / 2) {
    if (!this.layout) return;
    // Invert the readable horizontal projection without changing the zoom anchor.
    let lo = -100000,
      hi = this.layout.width + 100000;
    for (let i = 0; i < 50; i++) {
      const mid = (lo + hi) / 2;
      if (this.q.x(mid) < x - this.view.x) lo = mid;
      else hi = mid;
    }
    const wx = (lo + hi) / 2,
      wy = (y - this.view.y) / this.view.scale;
    this.view.scale = Math.max(0.005, Math.min(3, this.view.scale * factor));
    this.project();
    this.view.x = x - this.q.x(wx);
    this.view.y = y - this.q.y(wy);
    this.paint();
    this.changed();
  }
  pan(x, y) {
    this.view.x += x;
    this.view.y += y;
    this.paint();
    this.changed();
  }
  paint() {
    if (!this.layout || !this.plot.clientWidth || !this.plot.clientHeight)
      return;
    this.project();
    const { q, view: v, state: s, plot: p } = this;
    v.x = Math.max(32 - q.width, Math.min(p.clientWidth - 32, v.x));
    v.y = Math.max(32 - q.height, Math.min(p.clientHeight - 32, v.y));
    const px = (x) => q.x(x) + v.x,
      py = (y) => q.y(y) + v.y;
    const route = s.path(s.current),
      branch = s.paths(true, s.current),
      active = new Set([...route, ...branch.keys()]);
    const routed = [];
    const selectedEdge = (edge) =>
      s.current !== s.model.root &&
      active.has(edge.sources[0]) &&
      active.has(edge.targets[0]);
    const focused = this.nodes.contains(document.activeElement)
      ? document.activeElement.closest("[data-graph-node]")?.dataset.graphNode
      : undefined;
    for (const edge of this.layout.edges || [])
      for (const section of edge.sections || []) {
        const points = [
          section.startPoint,
          ...(section.bendPoints || []),
          section.endPoint,
        ].map((n) => ({ x: px(n.x), y: py(n.y) }));
        routed.push({
          edge,
          points,
          vertical: (this.bridges.get(section) || []).map((v) => ({
            x: px(v.x),
            top: py(v.top),
            bottom: py(v.bottom),
          })),
        });
      }
    routed.sort(
      (a, b) => Number(selectedEdge(a.edge)) - Number(selectedEdge(b.edge)),
    );
    this.lines.replaceChildren();
    this.lines.setAttribute(
      "viewBox",
      `0 0 ${p.clientWidth} ${p.clientHeight}`,
    );
    for (const { edge, points, vertical } of routed) {
      if (
        points.every((n) => n.x < -20) ||
        points.every((n) => n.x > p.clientWidth + 20) ||
        points.every((n) => n.y < -20) ||
        points.every((n) => n.y > p.clientHeight + 20)
      )
        continue;
      const selected = selectedEdge(edge),
        main =
          (s.direction === "out" ? edge.sources[0] : edge.targets[0]) ===
          s.model.root,
        compact = v.scale < 0.2 && !selected && !main;
      this.lines.append(
        svg("path", {
          d: edgePath(points, vertical),
          class: `graph-edge${selected ? " active" : ""}${compact ? " compact" : ""}`,
        }),
      );
      const b = points.at(-1),
        a = points.at(-2),
        angle = Math.atan2(b.y - a.y, b.x - a.x),
        length = compact ? 3 : 7;
      this.lines.append(
        svg("path", {
          d: `M ${b.x} ${b.y} L ${b.x - length * Math.cos(angle - 0.45)} ${b.y - length * Math.sin(angle - 0.45)} L ${b.x - length * Math.cos(angle + 0.45)} ${b.y - length * Math.sin(angle + 0.45)} Z`,
          class: `graph-arrow${selected ? " active" : ""}`,
        }),
      );
      for (const label of edge.labels || []) {
        const text = svg("text", {
          x: px(label.x),
          y: py(label.y) + 12,
          class: "graph-edge-label",
        });
        text.textContent = label.text;
        this.lines.append(text);
      }
    }
    const candidates = this.layout.children
      .map((n) => ({
        n,
        x: px(n.x),
        y: py(n.y + n.height / 2),
        width: q.x(n.x + n.width) - q.x(n.x),
      }))
      .filter(
        (n) =>
          n.x + n.width >= 0 &&
          n.x <= p.clientWidth &&
          n.y >= -32 &&
          n.y <= p.clientHeight + 32,
      )
      .sort(
        (a, b) => this.priority(b.n.id) - this.priority(a.n.id) || a.y - b.y,
      );
    const occupied = [],
      marks = [],
      fragment = document.createDocumentFragment();
    let labeled = 0;
    for (const { n, x, y, width } of candidates) {
      const node = s.nodes.get(n.id),
        height = s.model.kind === "cfg" && node.detail ? 54 : 30;
      const box = { x, y: y - height / 2, width, height };
      const named = !occupied.some(
        (b) =>
          box.x < b.x + b.width + 5 &&
          box.x + box.width + 5 > b.x &&
          box.y < b.y + b.height + 5 &&
          box.y + box.height + 5 > b.y,
      );
      const host = document.createElement(named ? "div" : "button");
      host.dataset.graphNode = n.id;
      host.className = `${named ? "graph-node" : "graph-glyph"}${n.id === s.current ? " current" : ""}${n.id === s.model.root ? " root" : ""}${s.model.kind === "cfg" ? " cfg" : ""}`;
      host.style.left = `${x}px`;
      host.style.top = `${named ? box.y : y - 6}px`;
      host.style.width = `${Math.max(28, width)}px`;
      if (named) {
        labeled++;
        occupied.push(box);
        const label = document.createElement("button");
        label.type = "button";
        label.className = "graph-name";
        label.textContent = node.name;
        label.style.fontSize = `${Math.max(11, Math.min(14, 12 * v.scale))}px`;
        label.title = node.name;
        label.setAttribute("aria-label", `Zoom into ${node.name}`);
        label.addEventListener("click", () => this.action("drill", n.id));
        host.append(label);
        if (s.model.kind === "cfg" && node.detail) {
          const detail = document.createElement("span");
          detail.className = "graph-detail";
          detail.textContent = node.detail;
          detail.title = node.detail;
          host.append(detail);
        }
        if (s.model.kind === "callgraph" && s.neighbors(n.id).length) {
          const toggle = document.createElement("button");
          toggle.type = "button";
          toggle.className = "graph-toggle";
          const open = s.expanded[s.direction].has(n.id);
          toggle.textContent = open ? "−" : "+";
          toggle.setAttribute("aria-expanded", String(open));
          toggle.setAttribute(
            "aria-label",
            `${open ? "Collapse" : "Expand"} ${s.direction === "out" ? "callees" : "callers"} of ${node.name}`,
          );
          toggle.addEventListener("click", () => this.action("toggle", n.id));
          host.append(toggle);
        }
      } else {
        host.type = "button";
        host.setAttribute("aria-label", `Zoom into ${node.name}`);
        host.title = node.name;
        host.addEventListener("click", () => this.action("drill", n.id));
      }
      if (named) fragment.append(host);
      else marks.push({ host, x: x + width / 2, y });
    }
    const underlay = document.createDocumentFragment();
    for (const mark of marks)
      if (
        !occupied.some(
          (b) =>
            mark.x + 9 > b.x &&
            mark.x - 9 < b.x + b.width &&
            mark.y + 6 > b.y &&
            mark.y - 6 < b.y + b.height,
        )
      )
        underlay.append(mark.host);
    underlay.append(fragment);
    this.nodes.replaceChildren(underlay);
    if (focused) {
      const target = [...this.nodes.children].find(
        (n) => n.dataset.graphNode === focused,
      );
      (target?.querySelector("button") || target)?.focus({
        preventScroll: true,
      });
    }
    this.plot.setAttribute(
      "aria-label",
      `${s.model.kind === "cfg" ? "Control flow" : "Call"} graph from ${s.model.name}; ${this.layout.children.length} nodes, ${candidates.length} in view`,
    );
    this.visibleCount = candidates.length;
    this.labelCount = labeled;
  }
  priority(id) {
    return id === this.state.current
      ? 100
      : id === this.state.model.root
        ? 90
        : this.state.neighbors(this.state.model.root).includes(id)
          ? 80
          : 0;
  }
}
