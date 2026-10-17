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
inline std::string include_inventory(
    const std::filesystem::path &root,
    const std::function<bool()> &allowed = {},
    const std::function<void(const std::filesystem::path &)> &watch = {}) {
  namespace fs = std::filesystem;
  if (!fs::exists(root))
    return "missing";
  std::vector<std::string> names;
  const auto canonical_root = fs::weakly_canonical(root);
  if (watch) {
    watch(root.parent_path());
    watch(root);
  }
  std::set<fs::path> visited{canonical_root};
  std::vector<fs::path> parents{canonical_root};
  fs::recursive_directory_iterator iterator(
      root, fs::directory_options::follow_directory_symlink),
      end;
  for (; iterator != end; ++iterator) {
    if (allowed && !allowed())
      throw std::runtime_error("include inventory interrupted");
    names.push_back(iterator->path().lexically_relative(root).generic_string());
    if (iterator->is_symlink()) {
      // A retargeted header alias can resolve to a different definition even
      // when every relative filename remains the same.
      names.push_back(std::string("\0symlink\0", 9) + names.back() + '\0' +
                      fs::read_symlink(iterator->path()).generic_string());
    }
    if (iterator->is_directory()) {
      if (watch && iterator->is_symlink())
        watch(iterator->path());
      // Resolve only symlinks. For an ordinary directory its parent's resolved
      // path plus its filename is already canonical; repeated realpath calls
      // otherwise re-stat every ancestor for every SDK directory on each TU.
      const auto depth = static_cast<std::size_t>(iterator.depth());
      const auto canonical = iterator->is_symlink()
                                 ? fs::weakly_canonical(iterator->path())
                                 : parents[depth] / iterator->path().filename();
      if (!visited.insert(canonical).second)
        iterator.disable_recursion_pending();
      else {
        if (watch)
          watch(canonical);
        parents.resize(depth + 2);
        parents[depth + 1] = canonical;
      }
    }
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
