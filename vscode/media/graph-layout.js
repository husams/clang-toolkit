export async function layoutGraph(elk, model, graph) {
  const cfg = model.kind === "cfg";
  return elk.layout({
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": cfg ? "DOWN" : "RIGHT",
      "elk.edgeRouting": "ORTHOGONAL",
      "elk.layered.spacing.nodeNodeBetweenLayers": "72",
      "elk.spacing.nodeNode": "28",
      "elk.layered.mergeEdges": String(!cfg),
      "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
      "elk.padding": "[top=24,left=24,bottom=24,right=24]",
    },
    children: graph.nodes.map((n) => ({
      id: n.id,
      width: Math.max(100, Math.min(600, n.name.length * 7.3 + 52)),
      height: cfg && n.detail ? 64 : 32,
    })),
    edges: graph.edges.map((e) => ({
      id: e.id,
      sources: [e.from],
      targets: [e.to],
      ...(e.label
        ? {
            labels: [
              { text: e.label, width: e.label.length * 7 + 8, height: 18 },
            ],
          }
        : {}),
    })),
  });
}

// Preserve readable horizontal columns while vertical zoom reveals more branches.
export function projection(layout, scale, cfg) {
  if (cfg)
    return {
      x: (x) => x * scale,
      y: (y) => y * scale,
      width: layout.width * scale,
      height: layout.height * scale,
    };
  const spans = layout.children
      .map((n) => [Math.max(0, n.x - 12), n.x + n.width + 12])
      .sort((a, b) => a[0] - b[0]),
    bands = [];
  for (const span of spans) {
    const last = bands.at(-1);
    if (last && span[0] <= last[1]) last[1] = Math.max(last[1], span[1]);
    else bands.push([...span]);
  }
  let world = 0,
    screen = 0;
  const parts = [];
  const add = (end, rate) => {
    if (end > world) {
      parts.push({ a: world, b: end, c: screen, rate });
      screen += (end - world) * rate;
      world = end;
    }
  };
  for (const [a, b] of bands) {
    add(a, scale);
    add(b, Math.max(scale, 11 / 12));
  }
  add(layout.width, scale);
  const x = (value) => {
    const p = parts.find((p) => value <= p.b) || parts.at(-1);
    return p ? p.c + (value - p.a) * p.rate : value * scale;
  };
  return {
    x,
    y: (y) => y * scale,
    width: screen,
    height: layout.height * scale,
  };
}

export function edgePath(points, vertical) {
  let path = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1],
      b = points[i];
    if (Math.abs(a.y - b.y) < 0.1) {
      const sign = Math.sign(b.x - a.x),
        lo = Math.min(a.x, b.x) + 6,
        hi = Math.max(a.x, b.x) - 6;
      const crossings = [
        ...new Set(
          vertical
            .filter(
              (v) =>
                v.x > lo && v.x < hi && a.y > v.top + 5 && a.y < v.bottom - 5,
            )
            .map((v) => Math.round(v.x)),
        ),
      ].sort((x, y) => sign * (x - y));
      let last = -Infinity;
      for (const x of crossings) {
        if (Math.abs(x - last) < 12) continue;
        path += ` L ${x - sign * 4} ${a.y} Q ${x} ${a.y - 7} ${x + sign * 4} ${a.y}`;
        last = x;
      }
    }
    path += ` L ${b.x} ${b.y}`;
  }
  return path;
}

// Find possible crossover bridges once per layout, never for every pan frame.
export function bridgeCandidates(layout) {
  const sections = (layout.edges || []).flatMap((e) => e.sections || []),
    vertical = [],
    result = new Map();
  const points = (section) => [
    section.startPoint,
    ...(section.bendPoints || []),
    section.endPoint,
  ];
  for (const section of sections) {
    const ps = points(section);
    for (let i = 1; i < ps.length; i++) {
      const a = ps[i - 1],
        b = ps[i];
      if (a.x === b.x)
        vertical.push({
          x: a.x,
          top: Math.min(a.y, b.y),
          bottom: Math.max(a.y, b.y),
        });
    }
  }
  vertical.sort((a, b) => a.x - b.x);
  for (const section of sections) {
    const ps = points(section),
      found = new Set();
    for (let i = 1; i < ps.length; i++) {
      const a = ps[i - 1],
        b = ps[i];
      if (a.y !== b.y) continue;
      const left = Math.min(a.x, b.x),
        right = Math.max(a.x, b.x);
      let lo = 0,
        hi = vertical.length;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (vertical[mid].x <= left) lo = mid + 1;
        else hi = mid;
      }
      for (let j = lo; j < vertical.length && vertical[j].x < right; j++)
        if (vertical[j].top < a.y && vertical[j].bottom > a.y)
          found.add(vertical[j]);
    }
    result.set(section, [...found]);
  }
  return result;
}
