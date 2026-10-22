#include "ctk/clang/cpp_snippet.hpp"
#include "ctk/clang/compilation_database.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <stdexcept>

namespace ctk::clang_layer {
namespace {
std::string header_directive(const std::string &header) {
  if (header.empty() || header.find_first_of("\r\n") != std::string::npos ||
      header.find('\0') != std::string::npos)
    throw std::invalid_argument(
        "snippet includes require nonempty header names");
  if ((header.front() == '<' && header.back() == '>') ||
      (header.front() == '"' && header.back() == '"')) {
    const auto name = header.substr(1, header.size() - 2);
    if (name.empty() || name.find_first_of("\"<>") != std::string::npos)
      throw std::invalid_argument("invalid snippet include: " + header);
    return "#include " + header + "\n";
  }
  if (header.find_first_of("\"<>") != std::string::npos)
    throw std::invalid_argument("invalid snippet include: " + header);
  return "#include \"" + header + "\"\n";
}
} // namespace

PreparedCppSnippet
prepare_cpp_snippet(const ctk::match::v1::ParseRequest &request) {
  if (!request.has_cpp_snippet())
    return {request, {}};
  if (!request.file_path().empty())
    throw std::invalid_argument(
        "file_path and cpp_snippet are mutually exclusive");
  const auto &snippet = request.cpp_snippet();
  if (snippet.code().find('\0') != std::string::npos ||
      snippet.settings_file().find('\0') != std::string::npos)
    throw std::invalid_argument(
        "snippet source and settings file cannot contain NUL bytes");
  const std::vector<std::string> overrides{request.compile_arguments().begin(),
                                           request.compile_arguments().end()};
  FileInput context{snippet.settings_file(),
                    request.frozen_profile() ? overrides
                                             : std::vector<std::string>{},
                    request.working_directory().empty()
                        ? std::filesystem::current_path().string()
                        : request.working_directory(),
                    request.compilation_database(), request.frozen_profile()};
  if (!std::filesystem::path(context.working_directory).is_absolute())
    throw std::invalid_argument(
        "absolute snippet working directory is required");
  const auto original_working = context.working_directory;
  const auto settings_path =
      snippet.settings_file().empty()
          ? std::filesystem::path{}
          : (std::filesystem::path(snippet.settings_file()).is_absolute()
                 ? std::filesystem::path(snippet.settings_file())
                 : std::filesystem::path(original_working) /
                       snippet.settings_file());
  if (!settings_path.empty() &&
      !std::filesystem::is_regular_file(settings_path))
    throw std::invalid_argument("settings source file is unavailable: " +
                                settings_path.string());
  context = resolve_snippet_compilation_command(context);
  if (!request.frozen_profile())
    context =
        transfer_snippet_compilation_command(std::move(context), overrides);
  auto directory =
      std::make_shared<ctk::platform::TemporaryDirectory>("ctk-snippet");
  const auto source = directory->path() / "snippet.cpp";
  std::ofstream output(source, std::ios::binary);
  if (!output)
    throw std::runtime_error("cannot create snippet source: " +
                             source.string());
  for (const auto &header : snippet.includes())
    output << header_directive(header);
  if (!snippet.translation_unit())
    output << "inline void ctk_snippet() {\n";
  // Diagnostics use snippet-relative line numbers; the file path remains the
  // real temporary .cpp so source retrieval continues to work normally.
  output << "#line 1\n" << snippet.code() << '\n';
  if (!snippet.translation_unit())
    output << "}\n";
  output.close();
  if (!output)
    throw std::runtime_error("cannot write snippet source: " + source.string());

  const auto borrowed_source =
      context.path.empty()
          ? settings_path
          : (std::filesystem::path(context.path).is_absolute()
                 ? std::filesystem::path(context.path)
                 : std::filesystem::path(original_working) / context.path);
  std::vector<std::string> snippet_arguments;
  if (!borrowed_source.empty()) {
    // The original source directory precedes every -iquote search directory.
    // Reproduce that ordering even though the physical file lives in /tmp.
    const std::vector<std::string> source_directory{
        "-iquote", borrowed_source.parent_path().string()};
    context.compile_arguments.insert(context.compile_arguments.begin(),
                                     source_directory.begin(),
                                     source_directory.end());
  } else {
    // Standalone snippets resolve quoted headers relative to the requested CWD.
    snippet_arguments.push_back("-iquote");
    snippet_arguments.push_back(context.working_directory);
  }
  // A borrowed header/C compilation command must still produce a C++ TU.
  snippet_arguments.push_back("-x");
  snippet_arguments.push_back("c++");
  const auto separator = std::find(context.compile_arguments.begin(),
                                   context.compile_arguments.end(), "--");
  context.compile_arguments.insert(separator, snippet_arguments.begin(),
                                   snippet_arguments.end());
  PreparedCppSnippet prepared{request, std::move(directory)};
  prepared.request.clear_cpp_snippet();
  prepared.request.set_file_path(source.string());
  prepared.request.set_working_directory(context.working_directory);
  prepared.request.set_compilation_database(context.compilation_database);
  prepared.request.clear_compile_arguments();
  for (const auto &argument : context.compile_arguments)
    prepared.request.add_compile_arguments(argument);
  prepared.request.set_frozen_profile(true);
  // Extra include lookup/language flags give the snippet its own profile.
  prepared.request.clear_expected_profile_id();
  return prepared;
}
} // namespace ctk::clang_layer
