#include "ctk/clang/project_index_extract.hpp"
#include "ctk/platform/index_worker.hpp"
#include "index/v1/index_service.pb.h"
#include <algorithm>
#include <cstdio>
#include <exception>
#include <fstream>
#include <iostream>
#include <system_error>

namespace {
int run_worker(int argc, char **argv, std::string &result_path,
               ctk::index::v1::IndexWorkerResponse &response) {
  std::string request_path;
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
  try {
    ctk::platform::lower_index_worker_priority();
  } catch (const std::system_error &error) {
    if (error.code() != std::errc::operation_not_permitted &&
        error.code() != std::errc::permission_denied)
      throw;
    // Scheduling policy is optional; denied priority changes must not prevent
    // an otherwise valid extraction from running.
    std::cerr << "ctk-index-worker: warning: " << error.what()
              << "; continuing with inherited priority\n";
  }
  ctk::index::v1::IndexWorkerRequest request;
  std::ifstream request_file(request_path, std::ios::binary);
  if (!request_file || !request.ParseFromIstream(&request_file)) {
    response.set_error("cannot read index worker request: " + request_path);
    return 3;
  }
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
    return response.success() ? 0 : 1;
  }
  ctk::clang_layer::ProjectIndexExtraction extraction;
  std::string error;
  std::vector<std::string> arguments(request.compile_arguments().begin(),
                                     request.compile_arguments().end());
  std::map<std::string, std::string> include_inventories;
  for (const auto &inventory : request.precomputed_include_inventories())
    include_inventories.insert_or_assign(inventory.path(), inventory.sha256());
  response.set_success(ctk::clang_layer::extract_project_index(
      request.source(), request.compile_commands_directory(),
      request.working_directory(), arguments, extraction, error,
      request.header_cache_directory(), &include_inventories));
  response.set_error(error);
  response.set_compile_context(extraction.compile_context);
  response.set_reused_header_symbols(extraction.reused_header_symbols);
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
  return response.success() ? 0 : 1;
}

int worker_main(int argc, char **argv) {
  std::string result_path;
  ctk::index::v1::IndexWorkerResponse response;
  int exit_code = 1;
  try {
    exit_code = run_worker(argc, argv, result_path, response);
  } catch (const std::exception &error) {
    response.Clear();
    response.set_error(std::string("index worker failed: ") + error.what());
  } catch (...) {
    response.Clear();
    response.set_error("index worker failed: unknown exception");
  }
  if (!response.error().empty())
    std::cerr << "ctk-index-worker: " << response.error() << '\n';
  if (result_path.empty())
    return exit_code;
  try {
    std::ofstream result_file(result_path, std::ios::binary | std::ios::trunc);
    if (!result_file) {
      std::cerr << "ctk-index-worker: cannot open result file: " << result_path
                << '\n';
      return 4;
    }
    const bool serialized = response.SerializeToOstream(&result_file);
    result_file.close();
    if (!serialized || !result_file) {
      std::cerr << "ctk-index-worker: cannot write result file: " << result_path
                << '\n';
      return 4;
    }
  } catch (const std::exception &error) {
    std::cerr << "ctk-index-worker: cannot write result file: " << result_path
              << ": " << error.what() << '\n';
    return 4;
  } catch (...) {
    std::cerr << "ctk-index-worker: cannot write result file: " << result_path
              << ": unknown exception\n";
    return 4;
  }
  return exit_code;
}
} // namespace

int main(int argc, char **argv) {
  try {
    return worker_main(argc, argv);
  } catch (const std::exception &error) {
    // Error reporting can itself fail (for example, after allocation failure).
    // Keep the executable boundary non-throwing even in that case.
    std::fprintf(stderr, "ctk-index-worker: failed to report error: %s\n",
                 error.what());
  } catch (...) {
    std::fputs("ctk-index-worker: failed to report unknown exception\n",
               stderr);
  }
  return 1;
}
