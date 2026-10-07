#include "project_inputs.hpp"
#include <algorithm>
#include <clang/Tooling/ArgumentsAdjusters.h>
#include <clang/Tooling/CompilationDatabase.h>
#include <filesystem>
#include <stdexcept>
namespace ctk::clang_layer {
namespace {
std::filesystem::path absolute_path(const std::filesystem::path &path,
                                    const std::filesystem::path &directory) {
  return (path.is_absolute() ? path : directory / path).lexically_normal();
}
} // namespace
ProjectInputs::ProjectInputs(const Project &project) {
  namespace fs = std::filesystem;
  const auto directory =
      project.compile_commands_dir.empty()
          ? fs::current_path()
          : fs::absolute(project.compile_commands_dir).lexically_normal();
  std::unique_ptr<clang::tooling::CompilationDatabase> database;
  auto selected = project.files;
  if (!project.compile_commands_dir.empty()) {
    std::string error;
    database = clang::tooling::CompilationDatabase::loadFromDirectory(
        directory.string(), error);
    if (!database)
      throw std::invalid_argument("cannot load compilation database: " + error);
    if (selected.empty()) {
      selected = database->getAllFiles();
      std::sort(selected.begin(), selected.end());
    }
  }
  if (selected.empty())
    throw std::invalid_argument(
        "project requires source files or a nonempty compilation database");
  for (const auto &selected_file : selected) {
    const auto path = absolute_path(selected_file, directory);
    FileInput input{path.string(), {}, directory.string()};
    if (database) {
      const auto commands = database->getCompileCommands(path.string());
      if (commands.empty())
        throw std::invalid_argument(
            "compile command not found for source file: " + path.string());
      // A Project has no configuration selector: use the first native DB
      // command.
      const auto &command = commands.front();
      const auto command_directory =
          absolute_path(command.Directory, directory);
      input.working_directory = command_directory.string();
      auto arguments = clang::tooling::getClangStripDependencyFileAdjuster()(
          command.CommandLine, path.string());
      arguments = clang::tooling::getClangStripOutputAdjuster()(arguments,
                                                                path.string());
      arguments = clang::tooling::getClangSyntaxOnlyAdjuster()(arguments,
                                                               path.string());
      const auto source = absolute_path(command.Filename, command_directory);
      for (std::size_t i = 1; i < arguments.size(); ++i) {
        const auto &argument = arguments[i];
        if (argument == "--" ||
            (argument.size() && argument.front() != '-' &&
             absolute_path(argument, command_directory) == source))
          continue;
        input.compile_arguments.push_back(argument);
      }
    }
    files_.push_back(std::move(input));
  }
}
} // namespace ctk::clang_layer
