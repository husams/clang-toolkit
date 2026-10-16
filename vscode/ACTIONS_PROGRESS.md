# Node based Actions prototype

- [x] YAML action files, validation, generated CTK callables and bundled actions.
- [x] Persistent console worker retaining file roots, match bindings and history.
- [x] Actions tab, collapsible arguments, bindings/files views and selected-node follow-ups.
- [ ] Live native, extension-host and regression verification; package the prototype.

Acceptance: parse a C++ file once, find a function, then run Find calls on its retained binding; both views preserve named binding/row associations. Invalid actions, stale input, cancellation and wrong return types preserve previous results or explicitly invalidate the context.
