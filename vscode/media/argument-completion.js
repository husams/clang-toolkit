/** A literal-value combobox; suggestion requests never execute an action. */
window.CtkArgumentCompletion = class ArgumentCompletion {
  static active;
  static sequence = 0;
  static close() {
    ArgumentCompletion.active?.hide();
  }
  static receive(message) {
    ArgumentCompletion.active?.receive(message);
  }

  constructor(input, parent, argument, revision, post) {
    this.input = input;
    this.argument = argument;
    this.revision = revision;
    this.post = post;
    this.items = [];
    this.index = 0;
    this.popup = document.createElement("div");
    this.popup.id = `argument-suggestions-${++ArgumentCompletion.sequence}`;
    this.popup.className = "argument-suggestions";
    this.popup.role = "listbox";
    this.popup.setAttribute(
      "aria-label",
      `${input.getAttribute("aria-label")} suggestions`,
    );
    this.popup.hidden = true;
    parent.append(this.popup);
    input.role = "combobox";
    input.autocomplete = "off";
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-controls", this.popup.id);
    input.setAttribute("aria-expanded", "false");
    input.addEventListener("focus", () => {
      if (!this.applying) this.schedule();
    });
    input.addEventListener("input", () => {
      if (!this.applying) this.schedule();
    });
    input.addEventListener("blur", () => this.hide());
    input.addEventListener("keydown", (event) => this.keydown(event));
  }
  schedule(immediate = false) {
    ArgumentCompletion.close();
    ArgumentCompletion.active = this;
    this.id = ++ArgumentCompletion.sequence;
    const id = this.id;
    this.timer = setTimeout(
      () => {
        if (document.activeElement !== this.input || !this.input.isConnected)
          return;
        this.value = this.input.value;
        if (this.value.length > 16384) {
          this.hide();
          return;
        }
        this.cursor = this.input.selectionStart ?? this.value.length;
        this.show([], "Loading suggestions…");
        this.post("nodeCompleteArgument", {
          id,
          revision: this.revision,
          argument: this.argument,
          value: this.value,
          cursor: this.cursor,
        });
      },
      immediate ? 0 : 120,
    );
  }
  receive(message) {
    if (
      message.id !== this.id ||
      message.revision !== this.revision ||
      document.activeElement !== this.input ||
      !this.input.isConnected ||
      this.input.value !== message.value ||
      this.input.selectionStart !== message.cursor
    )
      return;
    if (!message.items.length && !message.error) {
      this.hide();
      return;
    }
    this.show(message.items, message.error);
  }
  show(items, message = "") {
    this.items = items;
    this.index = 0;
    this.popup.replaceChildren();
    this.popup.hidden = false;
    this.input.setAttribute("aria-expanded", "true");
    if (!items.length) {
      const status = document.createElement("div");
      status.className = "completion-status";
      status.textContent = message;
      this.popup.append(status);
      this.input.removeAttribute("aria-activedescendant");
    }
    for (const [index, item] of items.entries()) {
      const option = document.createElement("button");
      option.type = "button";
      option.role = "option";
      option.id = `${this.popup.id}-${index}`;
      option.tabIndex = -1;
      option.title = item.text;
      const kind = document.createElement("span");
      kind.className = "completion-kind";
      kind.textContent =
        item.kind === "folder" ? "▸" : item.kind === "class" ? "◇" : "·";
      kind.setAttribute("aria-hidden", "true");
      const label = document.createElement("span");
      label.className = "completion-label";
      label.textContent = item.label;
      const detail = document.createElement("span");
      detail.className = "completion-detail";
      detail.textContent = item.detail;
      option.append(kind, label, detail);
      option.addEventListener("mousedown", (event) => event.preventDefault());
      option.addEventListener("click", () => this.apply(index));
      this.popup.append(option);
    }
    this.highlight();
  }
  highlight() {
    for (const [index, option] of [
      ...this.popup.querySelectorAll("button"),
    ].entries()) {
      option.setAttribute("aria-selected", String(index === this.index));
      if (index === this.index) {
        this.input.setAttribute("aria-activedescendant", option.id);
        option.scrollIntoView({ block: "nearest" });
      }
    }
  }
  keydown(event) {
    if (event.ctrlKey && event.key === " ") {
      event.preventDefault();
      event.stopPropagation();
      this.schedule(true);
      return;
    }
    if (event.key === "Escape" && ArgumentCompletion.active === this) {
      event.preventDefault();
      event.stopPropagation();
      this.hide();
    } else if (
      !this.popup.hidden &&
      ["ArrowDown", "ArrowUp"].includes(event.key)
    ) {
      event.preventDefault();
      event.stopPropagation();
      if (!this.items.length) return;
      this.index =
        (this.index +
          (event.key === "ArrowDown" ? 1 : -1) +
          this.items.length) %
        this.items.length;
      this.highlight();
    } else if (
      !this.popup.hidden &&
      this.items.length &&
      ["Enter", "Tab"].includes(event.key)
    ) {
      event.preventDefault();
      event.stopPropagation();
      this.apply(this.index);
    }
  }
  apply(index) {
    const item = this.items[index];
    if (!item) return;
    this.hide();
    this.applying = true;
    this.input.value = item.text;
    this.input.focus();
    this.input.setSelectionRange(item.text.length, item.text.length);
    this.input.dispatchEvent(new Event("input", { bubbles: true }));
    this.applying = false;
    if (item.kind === "folder") this.schedule(true);
  }
  hide() {
    clearTimeout(this.timer);
    this.id = ++ArgumentCompletion.sequence;
    this.popup.hidden = true;
    this.items = [];
    this.input.setAttribute("aria-expanded", "false");
    this.input.removeAttribute("aria-activedescendant");
    if (ArgumentCompletion.active === this)
      ArgumentCompletion.active = undefined;
  }
};
