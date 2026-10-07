#include "ctk/clang/cfg_backend.hpp"
#include "project_inputs.hpp"
#include <google/protobuf/util/json_util.h>
#include <stdexcept>
namespace ctk::clang_layer {
std::string cfg(const Project &project, const std::string &function) {
  if (function.empty())
    throw std::invalid_argument("function name is required");
  const ProjectInputs inputs(project);
  auto backend = make_cfg_backend();
  ctk::analysis::v1::CfgResponse response;
  CfgLimits limits{100, 10000, 100000, 4 * 1024 * 1024};
  for (const auto &file : inputs.files()) {
    ctk::analysis::v1::CfgRequest request;
    request.set_function(function);
    auto *target = request.mutable_file();
    target->set_file_path(file.path);
    target->set_working_directory(file.working_directory);
    for (const auto &argument : file.compile_arguments)
      target->add_compile_arguments(argument);
    auto result = backend->build(request, [] { return true; }, limits);
    if (result.code == MatchCode::NotFound)
      continue;
    if (result.code != MatchCode::Ok)
      throw std::runtime_error(result.message);
    limits.max_functions -= result.response.graphs_size();
    for (auto &graph : *result.response.mutable_graphs()) {
      limits.max_blocks -= graph.blocks_size();
      for (const auto &block : graph.blocks())
        limits.max_elements -= block.elements_size();
      response.add_graphs()->Swap(&graph);
    }
    if (response.ByteSizeLong() > 4 * 1024 * 1024)
      throw std::runtime_error("project CFG response limit exceeded");
  }
  if (response.graphs().empty())
    throw std::runtime_error("function definition not found in project");
  std::string json;
  google::protobuf::util::JsonPrintOptions options;
  options.preserve_proto_field_names = true;
  if (!google::protobuf::util::MessageToJsonString(response, &json, options)
           .ok())
    throw std::runtime_error("cannot serialize project CFG");
  if (json.size() > 4 * 1024 * 1024)
    throw std::runtime_error("project CFG JSON limit exceeded");
  return json;
}
} // namespace ctk::clang_layer
