#pragma once
#include <cstddef>
#include <cstdint>
namespace ctk::clang_layer {
struct CallGraphLimits {
  // Default when the request omits max_nodes; zero means unlimited.
  std::uint64_t max_nodes = 10000;
  std::size_t max_edges = 1000000;
  std::size_t max_bytes = 4 * 1024 * 1024;
};
} // namespace ctk::clang_layer
