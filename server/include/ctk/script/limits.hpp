#pragma once
#include <cstddef>
namespace ctk::script {
struct Limits {
  std::size_t max_steps = 100;
  std::size_t max_source_bytes = 1024 * 1024;
  std::size_t max_retained_bytes = 16 * 1024 * 1024;
  std::size_t max_response_bytes = 2147483648ULL;
};
} // namespace ctk::script
