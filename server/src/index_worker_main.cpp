#include "ctk/clang/project_index_extract.hpp"
#include "ctk/platform/index_worker.hpp"
#include "index/v1/index_service.pb.h"
#include <algorithm>
#include <fstream>
#include <iostream>

int main(int argc, char **argv) {
  std::string request_path, result_path;
  for (int i = 1; i < argc; ++i) {
    const std::string arg(argv[i]);
    if (arg == "--request" && i + 1 < argc)
      request_path = argv[++i];
    else if (arg == "--result" && i + 1 < argc)
      result_path = argv[++i];
    else
      return 2;
  }
  if (request_path.empty() || result_path.empty())
    return 2;
  ctk::platform::lower_index_worker_priority();
  ctk::index::v1::IndexWorkerRequest request;
  std::ifstream request_file(request_path, std::ios::binary);
  if (!request.ParseFromIstream(&request_file))
    return 3;
  ctk::index::v1::IndexWorkerResponse response;
  if (request.list_translation_units()) {
    std::vector<ctk::clang_layer::ProjectIndexCommand> units;
    std::string error;
    response.set_success(ctk::clang_layer::list_project_translation_units(
        request.compile_commands_directory(), units, error));
    response.set_error(error);
    for (const auto &command : units) {
      auto *unit = response.add_translation_units();
      unit->set_source(command.source);
      unit->set_working_directory(command.working_directory);
      for (const auto &argument : command.arguments)
        unit->add_compile_arguments(argument);
      unit->set_compile_context(command.serialized_context);
    }
    std::ofstream result_file(result_path, std::ios::binary | std::ios::trunc);
    if (!response.SerializeToOstream(&result_file))
      return 4;
    return response.success() ? 0 : 1;
  }
  ctk::clang_layer::ProjectIndexExtraction extraction;
  std::string error;
  std::vector<std::string> arguments(request.compile_arguments().begin(),
                                     request.compile_arguments().end());
  response.set_success(ctk::clang_layer::extract_project_index(
      request.source(), request.compile_commands_directory(),
      request.working_directory(), arguments, extraction, error));
  response.set_error(error);
  response.set_compile_context(extraction.compile_context);
  for (const auto &[path, hash] : extraction.dependencies) {
    auto *dependency = response.add_dependencies();
    dependency->set_path(path);
    dependency->set_sha256(hash);
  }
  for (const auto &symbol : extraction.symbols) {
    auto *output = response.add_symbols();
    output->set_usr(symbol.usr);
    output->set_name(symbol.name);
    output->set_qualified_name(symbol.qualified_name);
    output->set_kind(symbol.kind);
    output->set_file_path(symbol.file_path);
    output->set_line(symbol.line);
    output->set_column(symbol.column);
    output->set_signature(symbol.signature);
    output->set_byte_offset(symbol.byte_offset);
    output->set_is_definition(symbol.is_definition);
  }
  std::ofstream result_file(result_path, std::ios::binary | std::ios::trunc);
  if (!response.SerializeToOstream(&result_file))
    return 4;
  return response.success() ? 0 : 1;
}
