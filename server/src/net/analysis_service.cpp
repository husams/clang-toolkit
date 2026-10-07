#include "ctk/net/analysis_service.hpp"
#include "match_status.hpp"

namespace ctk::net {
grpc::Status AnalysisServiceAdapter::RunScript(
    grpc::ServerContext *context,
    const ctk::analysis::v1::ScriptRequest *request,
    ctk::analysis::v1::ScriptResponse *response) {
  auto result =
      scripts_.run(*request, [context] { return !context->IsCancelled(); });
  if (result.code == ctk::clang_layer::MatchCode::Ok)
    response->Swap(&result.response);
  return match_status(result.code, result.message, *context);
}
} // namespace ctk::net
