#pragma once

namespace ctk::platform {

// Reports whether local filesystem semantics support retaining open readers
// and relying on kernel directory notifications for index inputs.
bool supports_index_input_reuse(int descriptor);

// Shared allowance for retained watch and digest-reader descriptors. Temporary
// uncached reads and directory traversal use the reserved process capacity.
bool reserve_index_descriptor();
void release_index_descriptor();

} // namespace ctk::platform
