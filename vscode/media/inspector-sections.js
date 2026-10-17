export function sectionState(api) {
  const saved = api.getState()?.sections;
  const sections = new Map(
    Object.entries(saved && typeof saved === "object" ? saved : {}).filter(
      ([, open]) => typeof open === "boolean",
    ),
  );
  return (host) => {
    for (const group of host.querySelectorAll("details[data-section]")) {
      const title = group.dataset.section;
      if (sections.has(title)) group.open = sections.get(title);
      if (group.dataset.watched) continue;
      group.dataset.watched = "true";
      group.addEventListener("toggle", () => {
        if (!group.isConnected) return;
        sections.set(title, group.open);
        api.setState({ sections: Object.fromEntries(sections) });
      });
    }
  };
}
