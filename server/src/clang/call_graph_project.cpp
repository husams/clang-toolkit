#include "ctk/clang/call_graph_backend.hpp"
#include "project_inputs.hpp"
#include <google/protobuf/util/json_util.h>
#include <stdexcept>
namespace ctk::clang_layer {
std::string callgraph(const Project &project) {
  const ProjectInputs inputs(project);
  auto backend = make_call_graph_backend();
  CallGraphLimits limits{10000, 100000, 4 * 1024 * 1024};
  std::string json = "[";
  google::protobuf::util::JsonPrintOptions options;
  options.preserve_proto_field_names = true;
  bool first = true;
  for (const auto &file : inputs.files()) {
    ctk::analysis::v1::CallGraphRequest request;
    auto *target = request.mutable_file();
    target->set_file_path(file.path);
    target->set_working_directory(file.working_directory);
    for (const auto &argument : file.compile_arguments)
      target->add_compile_arguments(argument);
    auto result = backend->build(request, [] { return true; }, limits);
    if (result.code != MatchCode::Ok)
      throw std::runtime_error(result.message);
    limits.max_nodes -= result.response.nodes_size();
    limits.max_edges -= result.response.edges_size();
    std::string value;
    if (!google::protobuf::util::MessageToJsonString(result.response, &value,
                                                     options)
             .ok())
      throw std::runtime_error("cannot serialize project call graph");
    if (value.size() + json.size() + 2 > limits.max_bytes)
      throw std::runtime_error("project call graph response limit exceeded");
    if (!first)
      json += ",";
    first = false;
    json += value;
  }
  return json + "]";
}
} // namespace ctk::clang_layer
