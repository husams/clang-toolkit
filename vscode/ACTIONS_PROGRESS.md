# Node based Actions prototype

## Custom action creation, 0.2.2

- [x] Exercise Create action with both keyboard and mouse in the installed extension.
- [x] Open an editable, saved template immediately, using a unique file/name and retaining editor focus.
- [x] Preserve the selected node when creating a follow-up action.
- [x] Detect expired/closed native contexts and retain the C++ target across Refresh.
- [x] Verify the real editor workflow, package and update the installed prototype.

The previous Create flow opened a second naming prompt and returned focus to the
sidebar after opening the editor. Create now opens a pinned action editor directly,
with unique `my-action`, `my-action-2`, etc. names and no overwrites. Live UI
testing also reproduced a cursor-unavailable error when running a custom action
against an old context; expiry now marks the context stale with a Refresh message.

Validation: 21 extension checks, four native action scenarios with default helpers,
TypeScript/Biome and the complete isolated VS Code host passed. Installed 0.2.2
in the normal profile and reloaded only the trial window. Clicking Create action
opened `my-action-2.ctk-action` immediately with editor focus; Run displayed five
function matches from `actions-demo.cpp`. Isolated test windows closed normally.
No C++ or shared Python implementation changed; repository-wide limitations from
0.2.1 below remain.

## Helper compatibility and installation, 0.2.1

- [x] Reproduce the default helper preload error against the bundled runtime.
- [x] Bring the merged console pipe/tuple implementation into the prototype.
- [x] Verify actual default helper calls, node follow-ups and editor regressions.
- [x] Package, install and open a new trial window with Actions ready to use.

After fresh user confirmation, version 0.2.1 was installed in the normal VS Code
profile. Actions is open, and Order fields returned `demo::Order::quantity` using
the unchanged default helper library. Existing user windows were preserved.
Version 0.2.1 passed 84 pipe/tuple
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
