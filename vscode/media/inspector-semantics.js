export function renderSemantics(host, node, semantics, post, context) {
  const previous = new Map(
    [...host.querySelectorAll("details")].map((group) => [
      group.dataset.title,
      group.open,
    ]),
  );
  const sameNode = host.dataset.node === node.id;
  host.dataset.node = node.id;
  host.replaceChildren();
  function group(title) {
    const details = document.createElement("details"),
      summary = document.createElement("summary"),
      body = document.createElement("div");
    body.className = "section-body";
    details.dataset.title = title;
    details.dataset.section = title;
    details.open = sameNode ? (previous.get(title) ?? true) : true;
    summary.textContent = title;
    details.append(summary, body);
    host.append(details);
    return body;
  }
  if (semantics?.referencedDeclaration) {
    const reference = semantics.referencedDeclaration,
      details = group("Base declaration"),
      link = document.createElement("button");
    link.textContent = reference.name;
    link.title = `Inspect base class ${reference.name}`;
    link.disabled = context.running;
    link.dataset.vscodeContext = JSON.stringify({
      webviewSection: "ast-node",
      ctkAstNodeId: reference.nodeId,
      ctkAstContext: context.contextId,
      ctkAstCanRun: !context.running,
      preventDefaultContextMenuItems: true,
    });
    link.addEventListener("click", () =>
      post("related", { id: reference.nodeId }),
    );
    details.append(link);
  }
  if (semantics?.inheritance) {
    const details = group("Inheritance"),
      root = document.createElement("p");
    root.textContent = node.name;
    root.className = "inheritance-root";
    details.append(root);
    const list = document.createElement("ul");
    list.className = "inheritance";
    const levels = [list];
    for (const base of semantics.inheritance) {
      while (levels.length > base.depth + 1) levels.pop();
      if (levels.length <= base.depth) {
        const nested = document.createElement("ul");
        levels.at(-1).lastElementChild.append(nested);
        levels.push(nested);
      }
      const item = document.createElement("li"),
        access = base.access.replace("ACCESS_SPECIFIER_", "").toLowerCase();
      const label = `${base.name} · ${access}${base.virtual ? " virtual" : ""}${base.unresolved ? " · dependent / unresolved" : ""}`;
      if (base.nodeId && !base.unresolved) {
        const link = document.createElement("button");
        link.textContent = label;
        link.title = `Inspect base class ${base.name}`;
        link.disabled = context.running;
        link.dataset.vscodeContext = JSON.stringify({
          webviewSection: "ast-node",
          ctkAstNodeId: base.nodeId,
          ctkAstContext: context.contextId,
          ctkAstCanRun: !context.running,
          preventDefaultContextMenuItems: true,
        });
        link.addEventListener("click", () =>
          post("related", { id: base.nodeId }),
        );
        item.append(link);
      } else item.textContent = label;
      levels.at(-1).append(item);
    }
    details.append(list);
    if (!semantics.inheritance.length) {
      const empty = document.createElement("p");
      empty.textContent = "No base classes.";
      empty.className = "muted";
      details.append(empty);
    }
    if (semantics.notice) {
      const notice = document.createElement("p");
      notice.textContent = semantics.notice;
      notice.setAttribute("role", "status");
      details.append(notice);
    }
  }
  const sections = [...node.sections];
  if (semantics?.parameters) {
    const index = sections.findIndex(
      (section) => section.title === "Parameters",
    );
    const parameters = {
      title: "Parameters",
      columns: ["Name", "Type"],
      rows: semantics.parameters.map((parameter, index) => ({
        values: [parameter.name || `(unnamed ${index + 1})`, parameter.type],
      })),
    };
    if (index >= 0) sections[index] = parameters;
    else sections.unshift(parameters);
  }
  for (const section of sections) {
    const details = group(section.title);
    if (!section.rows.length) {
      const empty = document.createElement("p");
      empty.textContent =
        section.title === "Parameters" ? "No parameters." : "None.";
      empty.className = "muted";
      details.append(empty);
      continue;
    }
    const table = document.createElement("table"),
      head = document.createElement("thead"),
      heading = document.createElement("tr"),
      body = document.createElement("tbody");
    table.setAttribute("aria-label", section.title);
    for (const column of section.columns) {
      const cell = document.createElement("th");
      cell.scope = "col";
      cell.textContent = column;
      heading.append(cell);
    }
    head.append(heading);
    table.append(head, body);
    for (const row of section.rows) {
      const tr = document.createElement("tr");
      for (const [index, value] of row.values.entries()) {
        const cell = document.createElement("td");
        if (index === 0 && row.id) {
          const link = document.createElement("button");
          link.textContent = value;
          link.title = `Inspect ${value}`;
          link.addEventListener("click", () =>
            post("properties", { id: row.id }),
          );
          cell.append(link);
        } else cell.textContent = value || "—";
        tr.append(cell);
      }
      body.append(tr);
    }
    details.append(table);
  }
  host.hidden = !host.childElementCount;
}
