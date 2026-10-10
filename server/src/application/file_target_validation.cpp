#include "file_target_validation.hpp"
#include <filesystem>
#include <set>

namespace ctk::application::detail {
std::string invalid_file_target(const ctk::match::v1::FileMatchTarget &file) {
  if (file.compilation_database().find('\0') != std::string::npos)
    return "compilation_database cannot contain NUL bytes";
  if (file.file_path().empty() || file.working_directory().empty() ||
      !std::filesystem::path(file.working_directory()).is_absolute())
    return "file path and absolute working directory are required";
  const std::set<std::string> valued_flags{
      "-I",       "-isystem",     "-iquote",       "-idirafter",
      "-include", "-include-pch", "-fmodule-file", "-imacros",
      "-D",       "-U",           "-isysroot",     "--sysroot",
      "-target",  "--target",     "-resource-dir", "-x",
      "-arch",    "-Xclang",      "-mllvm"};
  for (int i = 0; i < file.compile_arguments_size(); ++i) {
    const auto &argument = file.compile_arguments(i);
    if (argument.empty() || argument[0] != '-' || argument == "--" ||
        argument == "-o" || argument.starts_with("-o") || argument == "-c" ||
        argument == "-S" || argument == "-E")
      return "compile_arguments must contain flags, not inputs or outputs";
    if (argument.starts_with("-std=") && !argument.starts_with("-std=c++") &&
        !argument.starts_with("-std=gnu++"))
      return "only C++ language modes are supported";
    if (valued_flags.contains(argument)) {
      if (++i == file.compile_arguments_size())
        return "compiler option requires a value";
      const auto &value = file.compile_arguments(i);
      if (argument == "-x" && value != "c++" && value != "c++-header")
        return "only C++ language modes are supported";
    } else if (argument.starts_with("-x") && argument != "-xc++" &&
               argument != "-xc++-header") {
      return "only C++ language modes are supported";
    }
  }
  return {};
}
std::string invalid_script_profile(
    const ctk::analysis::v1::ScriptCompilationProfile &profile) {
  ctk::match::v1::FileMatchTarget file;
  file.set_file_path("script-profile.cc");
  file.set_working_directory(profile.working_directory());
  file.set_compilation_database(profile.compilation_database());
  *file.mutable_compile_arguments() = profile.compile_arguments();
  return invalid_file_target(file);
}
} // namespace ctk::application::detail
