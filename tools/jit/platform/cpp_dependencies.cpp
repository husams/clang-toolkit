#include "cpp_dependencies.hpp"

#include <cerrno>
#include <cstdint>
#include <filesystem>
#include <set>
#include <stdexcept>
#include <sys/stat.h>

#include <llvm/ADT/SmallVector.h>
#include <llvm/ADT/StringExtras.h>
#include <llvm/ADT/STLExtras.h>

namespace ctk::jit {
namespace {

namespace fs = std::filesystem;

struct Stamp {
  std::uint64_t device;
  std::uint64_t inode;
  std::int64_t size;
  std::int64_t modified;
  std::int64_t changed;

  llvm::json::Value json() const {
    return llvm::json::Array{device, inode, size, modified, changed};
  }
};

std::int64_t nanos(const timespec &time) {
  return static_cast<std::int64_t>(time.tv_sec) * 1000000000 + time.tv_nsec;
}

std::optional<Stamp> stamp(const fs::path &path) {
  struct stat status {};
  if (::stat(path.c_str(), &status) != 0) {
    if (errno == ENOENT || errno == ENOTDIR)
      return std::nullopt;
    throw std::system_error(errno, std::generic_category(), "read include dependency");
  }
#if defined(__APPLE__)
  const auto modified = nanos(status.st_mtimespec);
  const auto changed = nanos(status.st_ctimespec);
#else
  const auto modified = nanos(status.st_mtim);
  const auto changed = nanos(status.st_ctim);
#endif
  return Stamp{static_cast<std::uint64_t>(status.st_dev),
               static_cast<std::uint64_t>(status.st_ino),
               status.st_size, modified, changed};
}

std::set<fs::path> headers(llvm::StringRef depfile) {
  std::set<fs::path> result;
  if (!depfile.consume_front("ctk-jit:"))
    return result;
  std::string token;
  const auto add_token = [&] {
    if (!token.empty()) {
      result.insert(fs::absolute(token));
      token.clear();
    }
  };
  while (!depfile.empty()) {
    const auto ch = depfile.front();
    depfile = depfile.drop_front();
    if (ch == '\\' && !depfile.empty()) {
      if (depfile.front() == '\n')
        add_token();
      else
        token += depfile.front();
      depfile = depfile.drop_front();
    } else if (llvm::isSpace(ch)) {
      add_token();
    } else {
      token += ch;
      if (ch == '$')
        depfile.consume_front("$");
    }
  }
  add_token();
  return result;
}

bool inside(const fs::path &path, const fs::path &root) {
  const auto relative = path.lexically_relative(root);
  return !relative.empty() && *relative.begin() != "..";
}

} // namespace

llvm::Expected<llvm::json::Value> dependency_stamp(const fs::path &path) {
  try {
    if (const auto identity = stamp(path))
      return identity->json();
    return llvm::createStringError(std::errc::no_such_file_or_directory,
                                   "cannot inspect %s", path.c_str());
  } catch (const std::system_error &error) {
    return llvm::createStringError(error.code(), "cannot inspect %s", path.c_str());
  }
}

std::optional<llvm::json::Object> observe_cpp_dependencies(
    llvm::StringRef depfile, llvm::StringRef diagnostics,
    std::chrono::system_clock::time_point started) {
  const auto includes = headers(depfile);
  if (includes.empty() || diagnostics.contains("[-Wdate-time]"))
    return std::nullopt;
  const auto [prelude, tail] = diagnostics.split("#include \"...\" search starts here:\n");
  const auto end = tail.find("\nEnd of search list.");
  if (end == llvm::StringRef::npos)
    return std::nullopt;
  const auto search = tail.take_front(end);

  try {
    std::set<fs::path> roots;
    llvm::SmallVector<llvm::StringRef, 16> lines;
    search.split(lines, '\n');
    for (auto line : lines) {
      line = line.trim();
      if (!line.empty() && !line.starts_with("#include")) {
        line.consume_back(" (framework directory)");
        roots.insert(fs::absolute(line.str()));
      }
    }
    if (roots.empty())
      return std::nullopt;
    llvm::json::Object observed;
    const auto since_epoch = std::chrono::duration_cast<std::chrono::nanoseconds>(
        started.time_since_epoch()).count();
    const auto record = [&](const fs::path &path) {
      const auto status = stamp(path);
      const auto name = path.string();
      if (observed.size() >= 16384 || (status && status->changed >= since_epoch))
        throw std::runtime_error("include inputs changed during preprocessing");
      observed[name] = status ? status->json() : llvm::json::Value(nullptr);
      return status;
    };
    lines.clear();
    prelude.split(lines, '\n');
    for (auto line : lines) {
      if (line.consume_front("ignoring nonexistent directory \"") &&
          line.consume_back("\"")) {
        if (record(fs::absolute(line.str())))
          return std::nullopt;
      } else if (line.consume_front("ignoring duplicate directory \"") &&
                 line.consume_back("\"")) {
        if (!record(fs::absolute(line.str())))
          return std::nullopt;
      }
    }

    std::vector<fs::path> physical_roots;
    for (const auto &root : roots)
      physical_roots.push_back(fs::canonical(root));
    for (const auto &header : includes) {
      if (!record(header) || !record(header.parent_path()))
        return std::nullopt;
      const auto parent = fs::canonical(header.parent_path());
      if (llvm::none_of(physical_roots, [&](const fs::path &root) {
            return inside(parent, root);
          }))
        roots.insert(header.parent_path());
    }

    std::vector<fs::path> pending(roots.begin(), roots.end());
    std::set<std::pair<std::uint64_t, std::uint64_t>> visited;
    while (!pending.empty()) {
      const auto directory = std::move(pending.back());
      pending.pop_back();
      const auto status = record(directory);
      if (!status)
        return std::nullopt;
      if (!visited.emplace(status->device, status->inode).second)
        continue;
      for (const auto &entry : fs::directory_iterator(directory)) {
        if (entry.is_directory())
          pending.push_back(entry.path());
        else if (entry.is_symlink())
          record(entry.path());
      }
    }
    return observed;
  } catch (const std::exception &) {
    return std::nullopt;
  }
}

bool cpp_dependencies_unchanged(const llvm::json::Object &observed) {
  if (observed.empty())
    return false;
  try {
    for (const auto &entry : observed) {
      const auto status = stamp(entry.first.str());
      if ((status ? status->json() : llvm::json::Value(nullptr)) != entry.second)
        return false;
    }
    return true;
  } catch (const std::system_error &) {
    return false;
  }
}

} // namespace ctk::jit
