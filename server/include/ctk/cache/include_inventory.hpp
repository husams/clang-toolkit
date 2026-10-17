#pragma once

#include <algorithm>
#include <filesystem>
#include <functional>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace ctk::cache {
// Names, not contents: ordinary edits use file digests; new/removed files can
// change include resolution even if no previously consumed file changed.
inline std::string
include_inventory(const std::filesystem::path &root,
                  const std::function<bool()> &allowed = {}) {
  namespace fs = std::filesystem;
  if (!fs::exists(root))
    return "missing";
  std::vector<std::string> names;
  std::set<fs::path> visited{fs::weakly_canonical(root)};
  fs::recursive_directory_iterator iterator(
      root, fs::directory_options::follow_directory_symlink),
      end;
  for (; iterator != end; ++iterator) {
    if (allowed && !allowed())
      throw std::runtime_error("include inventory interrupted");
    names.push_back(iterator->path().lexically_relative(root).generic_string());
    if (iterator->is_directory() &&
        !visited.insert(fs::weakly_canonical(iterator->path())).second)
      iterator.disable_recursion_pending();
    if (names.size() > 500000)
      throw std::runtime_error("include inventory exceeds 500000 paths");
  }
  std::sort(names.begin(), names.end());
  std::string result;
  for (const auto &name : names) {
    result += std::to_string(name.size()) + ':' + name;
    if (result.size() > 32 * 1024 * 1024)
      throw std::runtime_error("include inventory exceeds 32 MiB");
  }
  return result;
}
} // namespace ctk::cache
