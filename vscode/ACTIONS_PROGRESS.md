# Node based Actions prototype

## Helper compatibility and installation, 0.2.1

- [x] Reproduce the default helper preload error against the bundled runtime.
- [x] Bring the merged console pipe/tuple implementation into the prototype.
- [x] Verify actual default helper calls, node follow-ups and editor regressions.
- [ ] Package, install, reload the trial window and leave Actions ready to use.

The installation action is awaiting the fresh confirmation required by automatic
approval review for the locally built VSIX. Version 0.2.1 passed 84 pipe/tuple
regressions, 20 extension regressions, 15 editor-adapter checks, all three native
Actions scenarios with default helpers, and the complete real VS Code host.
Python units: 2,169 passed / 22 existing legacy-engine failures; selected console
end-to-end scenarios: 14 passed / 9 legacy-engine preload failures.

## Original 0.2.0 delivery

- [x] YAML action files, validation, generated CTK callables and bundled actions.
- [x] Persistent console worker retaining file roots, match bindings and history.
- [x] Actions tab, collapsible arguments, bindings/files views and selected-node follow-ups.
- [x] Live native, extension-host and regression verification; package the prototype.

Validation: 20 extension unit/worker checks, 15 Python editor adapter checks,
9 native extension checks and the full real VS Code host workflow passed.
All 363 C++ cases passed with isolated test storage. Repository-wide Python
units: 2,085 passed / 22 failed; end-to-end: 93 passed / 59 failed.
The repository suites are not green; existing external helper preloads and
native/console assertions remain. The opt-in action preload check also confirms
that the current default user library uses unsupported pipe syntax; configuring
the compatible checkout helper directory passes the action workflows.
See `docs/vscode-prototype-progress.md` and `vscode/README.md` for details.

Acceptance: parse a C++ file once, find a function, then run Find calls on its retained binding; both views preserve named binding/row associations. Invalid actions, stale input, cancellation and wrong return types preserve previous results or explicitly invalidate the context.
