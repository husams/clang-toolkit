#pragma once
#include "analysis/v1/script_request.pb.h"
#include "ctk/application/match_controller.hpp"
#include "ctk/script/engine.hpp"
#include <vector>
namespace ctk::application {
struct ScriptSourceRevision {
  std::string path;
  std::string kind;
  std::string content_digest;
  std::string validation_context;
};
class ScriptController final {
public:
  explicit ScriptController(
      CursorSettings settings = {},
      std::shared_ptr<ctk::clang_layer::IQueryEngine> engine = {},
      std::shared_ptr<OperationExecutor> executor = {});
  ctk::script::Result run(const ctk::analysis::v1::ScriptRequest &,
                          const ctk::clang_layer::IMatchBackend::Checkpoint &,
                          const std::string &owner = "local-user",
                          ctk::script::ExportSink export_sink = {});
  std::vector<std::vector<ScriptSourceRevision>> capture_source_revisions(
      const std::vector<ctk::match::v1::InputDescriptor> &inputs,
      const std::string &owner = "local-user",
      const std::string &resource_scope_id = {});

private:
  CursorSettings settings_;
  std::shared_ptr<ctk::clang_layer::IQueryEngine> engine_;
  std::shared_ptr<OperationExecutor> executor_;
};
} // namespace ctk::application
