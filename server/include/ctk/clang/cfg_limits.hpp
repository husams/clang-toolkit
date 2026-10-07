#pragma once
#include <cstddef>
namespace ctk::clang_layer {
struct CfgLimits {
  std::size_t max_functions = 1000;
  std::size_t max_blocks = 100000;
  std::size_t max_elements = 1000000;
  std::size_t max_bytes = 4 * 1024 * 1024;
};
} // namespace ctk::clang_layer
