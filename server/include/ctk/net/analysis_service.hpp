#pragma once
#include "analysis/v1/analysis_service.grpc.pb.h"
#include "ctk/application/script_controller.hpp"

namespace ctk::net {
class AnalysisServiceAdapter final
    : public ctk::analysis::v1::AnalysisService::Service {
public:
  explicit AnalysisServiceAdapter(application::ScriptController &scripts)
      : scripts_(scripts) {}
  grpc::Status RunScript(grpc::ServerContext *,
                         const ctk::analysis::v1::ScriptRequest *,
                         ctk::analysis::v1::ScriptResponse *) override;

private:
  application::ScriptController &scripts_;
};
} // namespace ctk::net
