#include "../file_values.hpp"

#include <ctime>
#include <filesystem>
#include <set>

#include <fnmatch.h>
#include <llvm/ADT/StringSwitch.h>
#include <llvm/Support/Format.h>
#include <sys/stat.h>

#include "../value_access.hpp"

namespace ctk::jit {
namespace {

namespace fs = std::filesystem;
using namespace value_access;

llvm::Error error(const llvm::Twine& message) {
  return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
}

bool wildcard(llvm::StringRef text) {
  return text.find_first_of("*?[") != llvm::StringRef::npos;
}

struct GlobStep {
  fs::path path;
  std::size_t component = 0;
};

llvm::Expected<std::set<fs::path>> expand(const fs::path& pattern, bool include_hidden,
                                          std::size_t limit, bool sources_only) {
  std::vector<std::string> components;
  for (const auto& part : pattern.relative_path()) {
    if (!part.empty() && part != ".") {
      components.push_back(part.string());
    }
  }
  const bool directories_only = pattern.filename().empty() || pattern.filename() == ".";
  const auto root = pattern.is_absolute() ? pattern.root_path() : fs::current_path();
  std::vector<GlobStep> pending{{root}};
  std::set<std::pair<fs::path, std::size_t>> seen;
  std::set<fs::path> found;
  while (!pending.empty()) {
    const auto current = std::move(pending.back());
    pending.pop_back();
    std::error_code issue;
    if (current.component == components.size()) {
      const auto status = fs::status(current.path, issue);
      if (issue || !fs::exists(status) || (directories_only && !fs::is_directory(status))) {
        continue;
      }
      auto path = current.path;
      if (sources_only) {
        if (!fs::is_regular_file(status)) {
          continue;
        }
        path = fs::canonical(path, issue);
        if (issue) {
          continue;
        }
      }
      found.insert(std::move(path));
      if (found.size() > limit) {
        return error(sources_only ? "match file list exceeds configured limit of 100 files"
                                  : "glob result exceeds 10000 entries");
      }
      continue;
    }

    const auto& part = components[current.component];
    if (part != "**" && !wildcard(part)) {
      pending.push_back({current.path / part, current.component + 1});
      continue;
    }
    if (!seen.emplace(current.path, current.component).second) {
      continue;
    }
    const bool recursive = part == "**";
    if (recursive) {
      pending.push_back({current.path, current.component + 1});
    }
    fs::directory_iterator iter(current.path, fs::directory_options::skip_permission_denied, issue);
    for (const fs::directory_iterator end; !issue && iter != end; iter.increment(issue)) {
      const auto& entry = *iter;
      const auto basename = entry.path().filename().string();
      if (!include_hidden && basename.starts_with('.') && !part.starts_with('.')) {
        continue;
      }
      if (!recursive) {
        if (::fnmatch(part.c_str(), basename.c_str(), FNM_NOESCAPE) == 0) {
          pending.push_back({entry.path(), current.component + 1});
        }
        continue;
      }
      std::error_code status_error;
      if (fs::is_directory(entry.symlink_status(status_error))) {
        pending.push_back({entry.path(), current.component});
      } else if (current.component + 1 == components.size()) {
        pending.push_back({entry.path(), current.component + 1});
      }
    }
  }
  return found;
}

std::optional<FileEntry> snapshot(const fs::path& path, const fs::path& cwd) {
  std::error_code error;
  const auto resolved = fs::canonical(path, error);
  if (error) {
    return std::nullopt;
  }
  struct stat metadata{};
  if (::stat(resolved.c_str(), &metadata) ||
      !(S_ISREG(metadata.st_mode) || S_ISDIR(metadata.st_mode))) {
    return std::nullopt;
  }
#ifdef __APPLE__
  const auto modified = metadata.st_mtimespec;
#else
  const auto modified = metadata.st_mtim;
#endif
  auto seconds = modified.tv_sec;
  auto micros = (modified.tv_nsec + 500) / 1000;
  if (micros == 1000000) {
    ++seconds;
    micros = 0;
  }
  struct tm utc{};
  char date[32];
  if (!::gmtime_r(&seconds, &utc) ||
      !std::strftime(date, sizeof(date), "%Y-%m-%dT%H:%M:%S", &utc)) {
    return std::nullopt;
  }
  std::string iso;
  llvm::raw_string_ostream timestamp(iso);
  timestamp << date;
  if (micros) {
    timestamp << llvm::format(".%06ld", static_cast<long>(micros));
  }
  timestamp << "+00:00";
  // Unlike lexically_relative, this retains explicit '..' components.
  const auto relative =
      path == cwd ? "." : path.string().substr(cwd.string().size() + (cwd == "/" ? 0 : 1));
  return FileEntry{relative, resolved.string(), std::move(iso),
                   static_cast<std::int64_t>(metadata.st_size), S_ISDIR(metadata.st_mode)};
}

} // namespace

const std::string* file_path(const Value& value, bool allow_directory) {
  if (const auto* path = as<std::string>(value)) {
    return path;
  }
  if (const auto* entry = object<FileEntry>(value);
      entry && (allow_directory || !entry->directory)) {
    return &entry->absolute;
  }
  return nullptr;
}

std::optional<Value> file_field(const FileEntry& entry, llvm::StringRef name) {
  if (name == "path") {
    return Value{entry.path};
  }
  if (name == "absolute") {
    return Value{entry.absolute};
  }
  if (name == "size") {
    return Value{entry.size};
  }
  if (name == "modified") {
    return Value{entry.modified};
  }
  const fs::path path(entry.path);
  if (name == "basename") {
    return Value{path == "." ? std::string{} : path.filename().string()};
  }
  if (name == "dirname") {
    return Value{path.has_parent_path() ? path.parent_path().string() : std::string(".")};
  }
  if (name == "parts") {
    std::vector<Value> parts;
    for (const auto& part : path) {
      if (part != ".") {
        parts.push_back({part.string()});
      }
    }
    return list(std::move(parts));
  }
  return std::nullopt;
}

Value file_record(const FileEntry& entry) {
  auto record = std::make_shared<Record>();
  record->set("path", {entry.path});
  record->set("absolute", {entry.absolute});
  record->set("size", {entry.size});
  record->set("modified", {entry.modified});
  return {std::move(record)};
}

extern "C" const Value* ctk_jit_glob_v1(Values* runtime, const Value* pattern) {
  const auto* text = as<std::string>(*pattern);
  if (!text || text->empty() || text->find('\0') != std::string::npos) {
    return runtime->fail("glob requires a nonempty relative pattern");
  }
  const fs::path path(*text);
  if (path.is_absolute()) {
    return runtime->fail("glob patterns must be relative to the session directory");
  }
  auto paths = expand(path, true, max_items, false);
  if (!paths) {
    return runtime->fail(llvm::toString(paths.takeError()));
  }
  std::vector<Value> results;
  const auto cwd = fs::current_path();
  for (const auto& candidate : *paths) {
    if (auto entry = snapshot(candidate, cwd)) {
      results.push_back({std::make_shared<FileEntry>(std::move(*entry))});
    }
  }
  return runtime->hold(list(std::move(results)));
}

llvm::Expected<std::optional<std::vector<std::string>>> match_paths(llvm::StringRef text) {
  fs::path path(text.str());
  std::error_code issue;
  if (fs::is_regular_file(path, issue)) {
    return std::nullopt;
  }
  issue.clear();
  const bool directory = fs::is_directory(path, issue);
  if (!directory && !wildcard(text)) {
    return std::nullopt;
  }
  constexpr std::size_t limit = 100;
  std::set<fs::path> matches;
  if (directory) {
    fs::recursive_directory_iterator it(path, fs::directory_options::skip_permission_denied, issue);
    for (const fs::recursive_directory_iterator end; !issue && it != end; it.increment(issue)) {
      const auto suffix = it->path().extension().string();
      if (!llvm::StringSwitch<bool>(suffix)
               .Cases({".c", ".cc", ".cpp", ".cxx", ".c++", ".C", ".m", ".mm"}, true)
               .Default(false)) {
        continue;
      }
      std::error_code file_error;
      if (it->is_regular_file(file_error)) {
        auto full = fs::canonical(it->path(), file_error);
        if (!file_error) {
          matches.insert(std::move(full));
        }
      }
      if (matches.size() > limit) {
        return error("match file list exceeds configured limit of 100 files");
      }
    }
  } else {
    auto expanded = expand(path, false, limit, true);
    if (!expanded) {
      return expanded.takeError();
    }
    matches = std::move(*expanded);
  }
  std::vector<std::string> result;
  for (const auto& match : matches) {
    result.push_back(match.string());
  }
  return result;
}

} // namespace ctk::jit
