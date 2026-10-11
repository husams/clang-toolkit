#pragma once
#include "analysis/v1/analysis_service.grpc.pb.h"
#include "ctk/application/call_graph_controller.hpp"
#include "ctk/application/batch_registry.hpp"
#include "ctk/application/cfg_controller.hpp"
#include "ctk/application/script_controller.hpp"
#include "ctk/application/traversal_controller.hpp"

namespace ctk::net {
class AnalysisServiceAdapter final
    : public ctk::analysis::v1::AnalysisService::Service {
public:
  explicit AnalysisServiceAdapter(application::TraversalController &controller,
                                  application::CfgController &cfg,
                                  application::CallGraphController &calls,
                                  application::ScriptController &scripts,
                                  application::BatchRegistry &batches)
      : controller_(controller), cfg_(cfg), calls_(calls), scripts_(scripts),
        batches_(batches) {}
  grpc::Status StartBatch(grpc::ServerContext *,
                          const ctk::analysis::v1::StartBatchRequest *,
                          ctk::analysis::v1::BatchRun *) override;
  grpc::Status BatchStatus(grpc::ServerContext *,
                           const ctk::analysis::v1::BatchRunRequest *,
                           ctk::analysis::v1::BatchRun *) override;
  grpc::Status CancelBatch(grpc::ServerContext *,
                           const ctk::analysis::v1::BatchControlRequest *,
                           ctk::analysis::v1::BatchRun *) override;
  grpc::Status ResumeBatch(grpc::ServerContext *,
                           const ctk::analysis::v1::BatchControlRequest *,
                           ctk::analysis::v1::BatchRun *) override;
  grpc::Status RetryBatch(grpc::ServerContext *,
                          const ctk::analysis::v1::BatchControlRequest *,
                          ctk::analysis::v1::BatchRun *) override;
  grpc::Status RunScript(grpc::ServerContext *,
                         const ctk::analysis::v1::ScriptRequest *,
                         ctk::analysis::v1::ScriptResponse *) override;
  grpc::Status Traverse(grpc::ServerContext *,
                        const ctk::analysis::v1::TraverseRequest *,
                        ctk::analysis::v1::TraverseResponse *) override;

  grpc::Status Cfg(grpc::ServerContext *, const ctk::analysis::v1::CfgRequest *,
                   ctk::analysis::v1::CfgResponse *) override;

  grpc::Status CallGraph(grpc::ServerContext *,
                         const ctk::analysis::v1::CallGraphRequest *,
                         ctk::analysis::v1::CallGraphResponse *) override;

private:
  application::TraversalController &controller_;
  application::CfgController &cfg_;
  application::CallGraphController &calls_;
  application::ScriptController &scripts_;
  application::BatchRegistry &batches_;
};
} // namespace ctk::net
