// Graph exploration is independent of the camera and never replaces graph data.
const validCamera = (c) =>
  c &&
  [c.scale, c.ax, c.ay].every(Number.isFinite) &&
  c.scale >= 0.005 &&
  c.scale <= 3;
export class GraphState {
  constructor(model, saved = {}) {
    this.model = model;
    this.nodes = new Map(model.nodes.map((n) => [n.id, n]));
    this.adjacency = { out: new Map(), in: new Map() };
    for (const edge of model.edges) {
      for (const [dir, from, to] of [
        ["out", edge.from, edge.to],
        ["in", edge.to, edge.from],
      ]) {
        if (!this.adjacency[dir].has(from)) this.adjacency[dir].set(from, []);
        if (!this.adjacency[dir].get(from).includes(to))
          this.adjacency[dir].get(from).push(to);
      }
    }
    this.direction =
      saved.direction === "in" && model.kind === "callgraph" ? "in" : "out";
    this.expanded = Object.fromEntries(
      ["out", "in"].map((dir) => [
        dir,
        new Set(
          Array.isArray(saved.expanded?.[dir])
            ? saved.expanded[dir].filter((id) => this.nodes.has(id))
            : model.kind === "cfg"
              ? model.nodes.map((n) => n.id)
              : [model.root],
        ),
      ]),
    );
    this.trail =
      Array.isArray(saved.trail) && saved.trail[0] === model.root
        ? [...new Set(saved.trail.filter((id) => this.nodes.has(id)))]
        : [model.root];
    this.cameras = Object.fromEntries(
      Object.entries(saved.cameras || {}).filter(
        ([key, c]) =>
          ["out", "in"].some(
            (dir) =>
              key.startsWith(`${dir}:`) &&
              this.nodes.has(key.slice(dir.length + 1)),
          ) && validCamera(c),
      ),
    );
    this.view = validCamera(saved.view) ? saved.view : undefined;
  }
  get current() {
    return this.trail.at(-1);
  }
  neighbors(id) {
    return this.adjacency[this.direction].get(id) || [];
  }
  paths(openOnly = true, start = this.model.root) {
    const paths = new Map([[start, [start]]]),
      queue = [start];
    for (let i = 0; i < queue.length; i++) {
      const id = queue[i];
      if (openOnly && !this.expanded[this.direction].has(id)) continue;
      for (const next of this.neighbors(id))
        if (!paths.has(next)) {
          paths.set(next, [...paths.get(id), next]);
          queue.push(next);
        }
    }
    return paths;
  }
  visible() {
    const paths = this.paths(),
      ids = new Set(paths.keys());
    const edges = this.model.edges.filter(
      (e) =>
        ids.has(e.from) &&
        ids.has(e.to) &&
        this.expanded[this.direction].has(
          this.direction === "out" ? e.from : e.to,
        ),
    );
    return { nodes: [...ids].map((id) => this.nodes.get(id)), edges };
  }
  reveal(id) {
    const path = this.paths(false).get(id);
    if (!path) return false;
    for (const parent of path.slice(0, -1))
      this.expanded[this.direction].add(parent);
    return true;
  }
  toggle(id) {
    const open = this.expanded[this.direction];
    if (open.has(id)) open.delete(id);
    else open.add(id);
    if (!this.paths().has(this.current)) this.trail = [this.model.root];
  }
  expandAll() {
    for (const id of this.paths(false).keys())
      this.expanded[this.direction].add(id);
  }
  visit(id, camera) {
    if (!this.nodes.has(id)) return;
    if (validCamera(camera))
      this.cameras[`${this.direction}:${this.current}`] = camera;
    const previous = this.trail.lastIndexOf(id);
    this.trail =
      previous >= 0 ? this.trail.slice(0, previous + 1) : [...this.trail, id];
    return previous >= 0 ? this.cameras[`${this.direction}:${id}`] : undefined;
  }
  snapshot(view) {
    return {
      direction: this.direction,
      expanded: Object.fromEntries(
        ["out", "in"].map((d) => [d, [...this.expanded[d]]]),
      ),
      trail: [...this.trail],
      cameras: { ...this.cameras },
      ...(validCamera(view) ? { view } : {}),
    };
  }
}
