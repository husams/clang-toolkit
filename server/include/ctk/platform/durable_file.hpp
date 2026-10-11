#pragma once

#include <filesystem>
#include <string_view>

namespace ctk::platform {
// Publish a complete replacement and synchronize the file and its parent chain.
// If this throws after rename, the caller must treat the outcome as unknown.
void durable_atomic_write(const std::filesystem::path &path,
                          std::string_view bytes);
} // namespace ctk::platform
