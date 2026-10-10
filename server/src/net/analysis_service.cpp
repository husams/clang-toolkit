#include "ctk/net/analysis_service.hpp"
#include "match_status.hpp"

namespace ctk::net {
namespace {
std::string owner(grpc::ServerContext &context) {
  const auto auth = context.auth_context();
  if (auth && auth->IsPeerAuthenticated()) {
    const auto identities = auth->GetPeerIdentity();
    if (!identities.empty())
      return std::string(identities.front().data(), identities.front().size());
  }
  return "local-user";
}
} // namespace
grpc::Status AnalysisServiceAdapter::StartBatch(
    grpc::ServerContext *context,
    const ctk::analysis::v1::StartBatchRequest *request,
    ctk::analysis::v1::BatchRun *response) {
  std::string message;
  const auto code = batches_.start(*request, owner(*context), *response, message);
  return match_status(code, message, *context);
}
grpc::Status AnalysisServiceAdapter::BatchStatus(
    grpc::ServerContext *context,
    const ctk::analysis::v1::BatchRunRequest *request,
    ctk::analysis::v1::BatchRun *response) {
  std::string message;
  const auto code = batches_.status(*request, owner(*context), *response, message);
  return match_status(code, message, *context);
}
grpc::Status AnalysisServiceAdapter::CancelBatch(
    grpc::ServerContext *context,
    const ctk::analysis::v1::BatchControlRequest *request,
    ctk::analysis::v1::BatchRun *response) {
  std::string message;
  const auto code = batches_.cancel(*request, owner(*context), *response, message);
  return match_status(code, message, *context);
}
grpc::Status AnalysisServiceAdapter::ResumeBatch(
    grpc::ServerContext *context,
    const ctk::analysis::v1::BatchControlRequest *request,
    ctk::analysis::v1::BatchRun *response) {
  std::string message;
  const auto code = batches_.resume(*request, owner(*context), *response, message);
  return match_status(code, message, *context);
}
grpc::Status AnalysisServiceAdapter::RetryBatch(
    grpc::ServerContext *context,
    const ctk::analysis::v1::BatchControlRequest *request,
    ctk::analysis::v1::BatchRun *response) {
  std::string message;
  const auto code = batches_.retry(*request, owner(*context), *response, message);
  return match_status(code, message, *context);
}
grpc::Status AnalysisServiceAdapter::RunScript(
    grpc::ServerContext *context,
    const ctk::analysis::v1::ScriptRequest *request,
    ctk::analysis::v1::ScriptResponse *response) {
  auto result =
      scripts_.run(*request, [context] { return !context->IsCancelled(); },
                   owner(*context));
  if (result.code == ctk::clang_layer::MatchCode::Ok)
    response->Swap(&result.response);
  return match_status(result.code, result.message, *context);
}
grpc::Status AnalysisServiceAdapter::Traverse(
    grpc::ServerContext *context,
    const ctk::analysis::v1::TraverseRequest *request,
    ctk::analysis::v1::TraverseResponse *response) {
  auto result = controller_.traverse(
      *request, [context] { return !context->IsCancelled(); }, owner(*context));
  if (result.code == ctk::clang_layer::MatchCode::Ok)
    response->Swap(&result.response);
  return match_status(result.code, result.message, *context);
}
grpc::Status
AnalysisServiceAdapter::Cfg(grpc::ServerContext *context,
                            const ctk::analysis::v1::CfgRequest *request,
                            ctk::analysis::v1::CfgResponse *response) {
  auto result =
      cfg_.build(*request, [context] { return !context->IsCancelled(); },
                 owner(*context));
  if (result.code == ctk::clang_layer::MatchCode::Ok)
    response->Swap(&result.response);
  return match_status(result.code, result.message, *context);
}
grpc::Status AnalysisServiceAdapter::CallGraph(
    grpc::ServerContext *context,
    const ctk::analysis::v1::CallGraphRequest *request,
    ctk::analysis::v1::CallGraphResponse *response) {
  auto result =
      calls_.build(*request, [context] { return !context->IsCancelled(); },
                   owner(*context));
  if (result.code == ctk::clang_layer::MatchCode::Ok)
    response->Swap(&result.response);
  return match_status(result.code, result.message, *context);
}
} // namespace ctk::net
