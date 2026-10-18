#pragma once

namespace ctk::platform {

// Reports whether local filesystem semantics support retaining open readers
// and relying on kernel directory notifications for index inputs.
bool supports_index_input_reuse(int descriptor);

} // namespace ctk::platform
