#pragma once
#include <stdexcept>

namespace project {
inline void leaf() {}
inline void check(int value) {
  if (value < 0)
    throw std::runtime_error("negative value");
  leaf();
}
} // namespace project

namespace vendor {
inline void trace() {}
} // namespace vendor
