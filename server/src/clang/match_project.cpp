#include "project_inputs.hpp"
#include <google/protobuf/util/json_util.h>
#include <stdexcept>
namespace ctk::clang_layer {
std::vector<std::string> match(const Project &project,
                               const std::string &matcher) {
  const ProjectInputs inputs(project);
  auto engine = make_query_engine();
  std::vector<std::string> rows;
  std::size_t bytes = 0;
  bool exceeded = false;
  google::protobuf::util::JsonPrintOptions options;
  options.preserve_proto_field_names = true;
  for (const auto &file : inputs.files()) {
    auto result = engine->match(
        file, matcher, [&] { return !exceeded; },
        [&](const IQueryEngine::Bindings &bindings) {
          ctk::match::v1::MatchResult row;
          for (const auto &[name, binding] : bindings)
            (*row.mutable_bindings())[name].CopyFrom(binding.value);
          std::string json;
          if (!google::protobuf::util::MessageToJsonString(row, &json, options)
                   .ok())
            throw std::runtime_error("cannot serialize project match");
          if (rows.size() >= 100000 || json.size() > 4 * 1024 * 1024 - bytes) {
            exceeded = true;
            return;
          }
          bytes += json.size();
          rows.push_back(std::move(json));
        });
    if (exceeded)
      throw std::runtime_error("project match result limit exceeded");
    if (!result.ok)
      throw std::runtime_error(result.message);
  }
  return rows;
}
} // namespace ctk::clang_layer
