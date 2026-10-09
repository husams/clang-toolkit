#pragma once
#include <cstdint>
#include <optional>

namespace ctk::platform {
// Current RSS when supported; unavailable is distinct from zero.
std::optional<std::uint64_t> resident_memory_bytes();
}
