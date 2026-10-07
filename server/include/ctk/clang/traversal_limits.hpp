#pragma once
#include <cstddef>

namespace ctk::clang_layer {
struct TraversalLimits {
  std::size_t max_nodes{100000};
  std::size_t max_bytes{4 * 1024 * 1024 - 4096};
};
} // namespace ctk::clang_layer
