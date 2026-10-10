#include "ctk/clang/file_discovery.hpp"
#include "ctk/clang/compilation_database.hpp"

#if __has_include(<clang/Options/Options.h>)
#include <clang/Options/Options.h>
#else
#include <clang/Driver/Options.h>
#endif
#include <clang/Tooling/ArgumentsAdjusters.h>
#include <clang/Tooling/CompilationDatabase.h>
#include <llvm/Option/Arg.h>
#include <llvm/Option/ArgList.h>
#include <llvm/Support/VirtualFileSystem.h>

#include <algorithm>
#include <filesystem>
#include <limits>
#include <regex>
#include <set>

namespace ctk::clang_layer {
namespace {
namespace fs = std::filesystem;

std::vector<std::string> normalized_flags(const FileInput &file) {
  // A private VFS avoids changing any shared filesystem's cwd.
  llvm::IntrusiveRefCntPtr<llvm::vfs::FileSystem> filesystem(
      llvm::vfs::createPhysicalFileSystem().release());
  if (auto error =
          filesystem->setCurrentWorkingDirectory(file.working_directory))
    throw std::invalid_argument("cannot use compilation working directory: " +
                                error.message());
  std::vector<std::string> expanded;
  for (const auto &argument : file.compile_arguments) {
    if (!argument.starts_with('@')) {
      expanded.push_back(argument);
      continue;
    }
    const auto path = fs::path(argument.substr(1));
    const auto absolute =
        path.is_absolute() ? path : fs::path(file.working_directory) / path;
    if (fs::file_size(absolute) > max_manifest_bytes)
      throw std::length_error(
          "compiler response file exceeds manifest byte limit");
    auto database = clang::tooling::expandResponseFiles(
        std::make_unique<clang::tooling::FixedCompilationDatabase>(
            file.working_directory, std::vector<std::string>{argument}),
        filesystem);
    auto response = database->getCompileCommands(file.path).front().CommandLine;
    response.erase(response.begin());
    response.pop_back();
    const auto separator = std::find(response.begin(), response.end(), "--");
    expanded.insert(expanded.end(), response.begin(), separator);
  }
  auto adjusted = clang::tooling::getClangStripDependencyFileAdjuster()(
      expanded, file.path);
  adjusted = clang::tooling::getClangStripOutputAdjuster()(adjusted, file.path);
  adjusted = clang::tooling::getClangSyntaxOnlyAdjuster()(adjusted, file.path);
  std::vector<const char *> argv;
  for (const auto &argument : adjusted)
    argv.push_back(argument.c_str());
  unsigned missing_index = 0, missing_count = 0;
#if __has_include(<clang/Options/Options.h>)
  const auto &options = clang::getDriverOptTable();
  const auto input_option = clang::options::OPT_INPUT;
  const auto separator_option = clang::options::OPT__DASH_DASH;
#else
  const auto &options = clang::driver::getDriverOptTable();
  const auto input_option = clang::driver::options::OPT_INPUT;
  const auto separator_option = clang::driver::options::OPT__DASH_DASH;
#endif
  const auto parsed = options.ParseArgs(argv, missing_index, missing_count);
  if (missing_count)
    throw std::invalid_argument("missing argument for compiler option: " +
                                adjusted.at(missing_index));
  llvm::opt::ArgStringList rendered;
  for (const auto *argument : parsed) {
    if (argument->getOption().getID() != input_option &&
        argument->getOption().getID() != separator_option)
      argument->render(parsed, rendered);
  }
  std::vector<std::string> flags;
  for (const auto *argument : rendered)
    flags.emplace_back(argument);
  return flags;
}

bool source_path(const fs::path &path) {
  const std::set<std::string> suffixes{".c",   ".cc", ".cpp", ".cxx",
                                       ".c++", ".C",  ".m",   ".mm"};
  return suffixes.contains(path.extension().string());
}

std::regex glob_expression(const std::string &pattern) {
  std::string result = "^";
  for (std::size_t i = 0; i < pattern.size(); ++i) {
    const auto c = pattern[i];
    if (c == '*') {
      if (i + 1 < pattern.size() && pattern[i + 1] == '*') {
        ++i;
        if (i + 1 < pattern.size() && pattern[i + 1] == '/') {
          ++i;
          result += "(?:.*/)?";
        } else
          result += ".*";
      } else
        result += "[^/]*";
    } else if (c == '?')
      result += "[^/]";
    else if (c == '[') {
      const auto end = pattern.find(']', i + 1);
      if (end == std::string::npos)
        throw std::invalid_argument("unterminated glob character class");
      result += '[';
      if (i + 1 < end && pattern[i + 1] == '!') {
        result += '^';
        ++i;
      }
      result += pattern.substr(i + 1, end - i - 1);
      result += ']';
      i = end;
    } else {
      if (std::string_view(".^$|(){}+\\").find(c) != std::string_view::npos)
        result += '\\';
      result += c;
    }
  }
  return std::regex(result + '$', std::regex::ECMAScript);
}
} // namespace

ResolvedFileDescriptor
resolve_file_descriptor(const ctk::match::v1::InputDescriptor &input) {
  if (input.file_path().empty() ||
      input.file_path().find('\0') != std::string::npos)
    throw std::invalid_argument(
        "nonempty source path without NUL bytes is required");
  const auto &profile = input.profile();
  if (profile.working_directory().find('\0') != std::string::npos ||
      profile.compilation_database().find('\0') != std::string::npos)
    throw std::invalid_argument("compilation context cannot contain NUL bytes");
  FileInput file{
      input.file_path(),
      {profile.compile_arguments().begin(), profile.compile_arguments().end()},
      profile.working_directory().empty() ? fs::current_path().string()
                                          : profile.working_directory(),
      profile.compilation_database(),
      profile.frozen()};
  if (!fs::path(file.working_directory).is_absolute())
    throw std::invalid_argument(
        "absolute serving-machine working directory is required");
  // Resolve the caller's source spelling before a database command selects a
  // different compiler cwd. Database lookup may canonicalize for matching, but
  // must not change the authoritative radix/VFS spelling used for acquisition.
  const auto source_spelling =
      (fs::path(file.path).is_absolute()
           ? fs::path(file.path)
           : fs::path(file.working_directory) / file.path)
          .lexically_normal()
          .string();
  file = resolve_compilation_command(file);
  // The cache's authoritative radix keys preserve path spelling. Resolving
  // symlinks here changes compiler include lookup and VFS-overlay semantics.
  file.working_directory =
      fs::path(file.working_directory).lexically_normal().string();
  file.path = source_spelling;
  if (!fs::is_regular_file(file.path))
    throw std::invalid_argument("source file is unavailable: " + file.path);
  file.compile_arguments = normalized_flags(file);
  file.compilation_profile_frozen = true;
  const auto identity = resolved_compilation_profile(file);
  if (!profile.profile_id().empty() && profile.profile_id() != identity)
    throw ProfileMismatch("compilation profile changed for " + file.path);
  ctk::match::v1::InputDescriptor descriptor;
  descriptor.set_file_path(file.path);
  auto *frozen = descriptor.mutable_profile();
  frozen->set_profile_id(identity);
  frozen->set_working_directory(file.working_directory);
  frozen->set_compilation_database(file.compilation_database);
  frozen->set_frozen(true);
  for (const auto &argument : file.compile_arguments)
    frozen->add_compile_arguments(argument);
  const auto bytes = fs::file_size(file.path);
  descriptor.set_source_bytes(bytes);
  // Admission estimate, deliberately separate from measured native ownership
  // and process RSS. Imported headers can make the actual snapshot larger.
  const auto scaled = bytes > std::numeric_limits<std::uint64_t>::max() / 64
                          ? std::numeric_limits<std::uint64_t>::max()
                          : bytes * 64;
  descriptor.set_estimated_parse_bytes(
      std::max<std::uint64_t>(16ULL * 1024 * 1024, scaled));
  return {std::move(file), std::move(descriptor)};
}

ctk::match::v1::DiscoverFilesResponse
discover_file_descriptors(const ctk::match::v1::DiscoverFilesRequest &request,
                          const std::function<bool()> &checkpoint) {
  const auto input_limit =
      request.has_max_inputs() ? request.max_inputs() : max_manifest_inputs;
  const auto byte_limit = request.has_max_metadata_bytes()
                              ? request.max_metadata_bytes()
                              : max_manifest_bytes;
  if (!input_limit || input_limit > max_manifest_inputs || !byte_limit ||
      byte_limit > max_manifest_bytes)
    throw std::invalid_argument(
        "manifest limits must be positive and within server limits");
  if (request.ByteSizeLong() > byte_limit)
    throw std::length_error(
        "discovery request exceeds manifest metadata limit");
  ctk::match::v1::DiscoverFilesResponse response;
  std::set<std::pair<std::string, std::string>> identities;
  std::uint64_t visited = 0;
  auto check = [&] {
    if (!checkpoint())
      throw std::runtime_error("file discovery cancelled");
    if (++visited > max_discovery_entries)
      throw std::length_error("file discovery traversal limit exceeded");
  };
  auto admit = [&](const ctk::match::v1::InputDescriptor &candidate) {
    check();
    auto resolved = resolve_file_descriptor(candidate);
    if (!identities
             .emplace(resolved.descriptor.file_path(),
                      resolved.descriptor.profile().profile_id())
             .second)
      return;
    if (static_cast<std::uint64_t>(response.inputs_size()) >= input_limit)
      throw std::length_error("file discovery input limit exceeded");
    *response.add_inputs() = std::move(resolved.descriptor);
    if (response.ByteSizeLong() > byte_limit)
      throw std::length_error("file discovery metadata byte limit exceeded");
  };
  for (const auto &input : request.inputs())
    admit(input);
  const auto cwd = request.profile().working_directory().empty()
                       ? fs::current_path()
                       : fs::path(request.profile().working_directory());
  if (!cwd.is_absolute())
    throw std::invalid_argument(
        "absolute serving-machine working directory is required");
  std::set<std::string> paths;
  auto add_path = [&](const fs::path &path) {
    paths.insert(path.lexically_normal().string());
    if (paths.size() > input_limit)
      throw std::length_error("file discovery input limit exceeded");
  };
  for (const auto &spelling : request.paths()) {
    check();
    if (spelling.find('\0') != std::string::npos || spelling.empty())
      throw std::invalid_argument(
          "discovery paths must be nonempty and contain no NUL bytes");
    const auto absolute =
        (fs::path(spelling).is_absolute() ? fs::path(spelling) : cwd / spelling)
            .lexically_normal();
    const auto pattern = absolute.generic_string();
    const auto wildcard = pattern.find_first_of("*?[");
    if (wildcard == std::string::npos && fs::is_regular_file(absolute)) {
      add_path(absolute);
      continue;
    }
    fs::path root = absolute;
    std::optional<std::regex> expression;
    if (wildcard != std::string::npos) {
      const auto slash = pattern.rfind('/', wildcard);
      root = slash == std::string::npos
                 ? cwd
                 : fs::path(pattern.substr(0, slash + 1));
      expression = glob_expression(pattern);
    }
    if (!fs::is_directory(root)) {
      response.add_diagnostics("discovery path unavailable: " + spelling);
      if (response.ByteSizeLong() > byte_limit)
        throw std::length_error(
            "file discovery diagnostic byte limit exceeded");
      continue;
    }
    for (const auto &entry : fs::recursive_directory_iterator(root)) {
      check();
      if (entry.is_regular_file() && source_path(entry.path()) &&
          (!expression ||
           std::regex_match(entry.path().lexically_normal().generic_string(),
                            *expression)))
        add_path(entry.path());
    }
  }
  for (const auto &path : paths) {
    ctk::match::v1::InputDescriptor candidate;
    candidate.set_file_path(path);
    *candidate.mutable_profile() = request.profile();
    admit(candidate);
  }
  std::sort(response.mutable_inputs()->begin(),
            response.mutable_inputs()->end(), [](const auto &a, const auto &b) {
              return std::pair(a.file_path(), a.profile().profile_id()) <
                     std::pair(b.file_path(), b.profile().profile_id());
            });
  response.set_metadata_bytes(response.ByteSizeLong());
  if (response.ByteSizeLong() > byte_limit)
    throw std::length_error("file discovery metadata byte limit exceeded");
  return response;
}
} // namespace ctk::clang_layer
