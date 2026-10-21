#pragma once

#include <algorithm>
#include <cstddef>
#include <filesystem>
#include <functional>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <vector>

namespace ctk::cache {
inline std::string canonical_include_path(const std::filesystem::path &path) {
  namespace fs = std::filesystem;
  std::error_code error;
  const auto canonical = fs::weakly_canonical(path, error);
  return (error ? fs::absolute(path).lexically_normal() : canonical).string();
}

// Keep this argument parser shared by the controller and extraction worker so
// their inventory keys describe exactly the same include search roots.
inline std::vector<std::string>
include_roots(const std::string &source, const std::string &working_directory,
              const std::vector<std::string> &arguments) {
  namespace fs = std::filesystem;
  std::set<std::string> roots{
      canonical_include_path(fs::path(source).parent_path())};
  for (std::size_t i = 0; i < arguments.size(); ++i) {
    const auto &argument = arguments[i];
    std::string path;
    if ((argument == "-I" || argument == "-iquote" || argument == "-isystem" ||
         argument == "-idirafter" || argument == "-F" ||
         argument == "-iframework") &&
        i + 1 < arguments.size())
      path = arguments[++i];
    else if (argument.starts_with("-I") && argument.size() > 2)
      path = argument.substr(2);
    else {
      for (const char *option :
           {"-iquote", "-isystem", "-idirafter", "-F", "-iframework"}) {
        const std::string_view prefix(option);
        if (argument.starts_with(prefix) && argument.size() > prefix.size()) {
          path = argument.substr(prefix.size());
          break;
        }
      }
    }
    if (!path.empty())
      roots.insert(canonical_include_path(
          fs::path(path).is_absolute() ? fs::path(path)
                                       : fs::path(working_directory) / path));
  }
  return {roots.begin(), roots.end()};
}
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
  }
  std::sort(names.begin(), names.end());
  std::string result;
  for (const auto &name : names) {
    result += std::to_string(name.size()) + ':' + name;
  }
  return result;
}
} // namespace ctk::cache
