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
  const auto code =
      batches_.start(*request, owner(*context), *response, message);
  return match_status(code, message, *context);
}
grpc::Status AnalysisServiceAdapter::BatchStatus(
    grpc::ServerContext *context,
    const ctk::analysis::v1::BatchRunRequest *request,
    ctk::analysis::v1::BatchRun *response) {
  std::string message;
  const auto code =
      batches_.status(*request, owner(*context), *response, message);
  return match_status(code, message, *context);
}
grpc::Status AnalysisServiceAdapter::CancelBatch(
    grpc::ServerContext *context,
    const ctk::analysis::v1::BatchControlRequest *request,
    ctk::analysis::v1::BatchRun *response) {
  std::string message;
  const auto code =
      batches_.cancel(*request, owner(*context), *response, message);
  return match_status(code, message, *context);
}
grpc::Status AnalysisServiceAdapter::ResumeBatch(
    grpc::ServerContext *context,
    const ctk::analysis::v1::BatchControlRequest *request,
    ctk::analysis::v1::BatchRun *response) {
  std::string message;
  const auto code =
      batches_.resume(*request, owner(*context), *response, message);
  return match_status(code, message, *context);
}
grpc::Status AnalysisServiceAdapter::RetryBatch(
    grpc::ServerContext *context,
    const ctk::analysis::v1::BatchControlRequest *request,
    ctk::analysis::v1::BatchRun *response) {
  std::string message;
  const auto code =
      batches_.retry(*request, owner(*context), *response, message);
  return match_status(code, message, *context);
}
grpc::Status AnalysisServiceAdapter::RunScript(
    grpc::ServerContext *context,
    const ctk::analysis::v1::ScriptRequest *request,
    ctk::analysis::v1::ScriptResponse *response) {
  auto result = scripts_.run(
      *request, [context] { return !context->IsCancelled(); }, owner(*context));
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
grpc::Status AnalysisServiceAdapter::StreamTraverse(
    grpc::ServerContext *context,
    const ctk::analysis::v1::TraverseRequest *request,
    grpc::ServerWriter<ctk::analysis::v1::TraverseStreamEvent> *writer) {
  auto result = controller_.traverse_stream(
      *request, [context] { return !context->IsCancelled(); },
      [writer](const ctk::analysis::v1::TraversalNode &node,
               std::string &message) {
        ctk::analysis::v1::TraverseStreamEvent event;
        event.mutable_node()->CopyFrom(node);
        if (!writer->Write(event)) {
          message = "AST traversal stream closed";
          return ctk::clang_layer::MatchCode::Cancelled;
        }
        return ctk::clang_layer::MatchCode::Ok;
      },
      owner(*context));
  if (result.code == ctk::clang_layer::MatchCode::Ok) {
    ctk::analysis::v1::TraverseStreamEvent event;
    event.mutable_completed()->set_node_count(result.node_count);
    event.mutable_completed()->set_depth_limited(
        result.response.depth_limited());
    if (!writer->Write(event)) {
      result.code = ctk::clang_layer::MatchCode::Cancelled;
      result.message = "AST traversal stream closed before completion";
    }
  }
  return match_status(result.code, result.message, *context);
}
grpc::Status
AnalysisServiceAdapter::Cfg(grpc::ServerContext *context,
                            const ctk::analysis::v1::CfgRequest *request,
                            ctk::analysis::v1::CfgResponse *response) {
  auto result = cfg_.build(
      *request, [context] { return !context->IsCancelled(); }, owner(*context));
  if (result.code == ctk::clang_layer::MatchCode::Ok)
    response->Swap(&result.response);
  return match_status(result.code, result.message, *context);
}
grpc::Status AnalysisServiceAdapter::StreamCfg(
    grpc::ServerContext *context, const ctk::analysis::v1::CfgRequest *request,
    grpc::ServerWriter<ctk::analysis::v1::CfgStreamEvent> *writer) {
  auto result = cfg_.build_stream(
      *request, [context] { return !context->IsCancelled(); },
      [writer](const ctk::analysis::v1::CfgStreamEvent &event,
               std::string &message) {
        if (!writer->Write(event)) {
          message = "CFG stream closed";
          return ctk::clang_layer::MatchCode::Cancelled;
        }
        return ctk::clang_layer::MatchCode::Ok;
      },
      owner(*context));
  if (result.code == ctk::clang_layer::MatchCode::Ok) {
    ctk::analysis::v1::CfgStreamEvent event;
    auto *completed = event.mutable_completed();
    completed->set_graph_count(result.graph_count);
    completed->set_block_count(result.block_count);
    completed->set_element_count(result.element_count);
    if (!writer->Write(event)) {
      result.code = ctk::clang_layer::MatchCode::Cancelled;
      result.message = "CFG stream closed before completion";
    }
  }
  return match_status(result.code, result.message, *context);
}
grpc::Status AnalysisServiceAdapter::CallGraph(
    grpc::ServerContext *context,
    const ctk::analysis::v1::CallGraphRequest *request,
    ctk::analysis::v1::CallGraphResponse *response) {
  auto result = calls_.build(
      *request, [context] { return !context->IsCancelled(); }, owner(*context));
  if (result.code == ctk::clang_layer::MatchCode::Ok)
    response->Swap(&result.response);
  return match_status(result.code, result.message, *context);
}
grpc::Status AnalysisServiceAdapter::StreamCallGraph(
    grpc::ServerContext *context,
    const ctk::analysis::v1::CallGraphRequest *request,
    grpc::ServerWriter<ctk::analysis::v1::CallGraphStreamEvent> *writer) {
  auto result = calls_.build_stream(
      *request, [context] { return !context->IsCancelled(); },
      [writer](const ctk::analysis::v1::CallGraphStreamEvent &event,
               std::string &message) {
        if (!writer->Write(event)) {
          message = "call graph stream closed";
          return ctk::clang_layer::MatchCode::Cancelled;
        }
        return ctk::clang_layer::MatchCode::Ok;
      },
      owner(*context));
  if (result.code == ctk::clang_layer::MatchCode::Ok) {
    if (context->IsCancelled()) {
      result.code = ctk::clang_layer::MatchCode::Cancelled;
      result.message = "call graph stream cancelled before completion";
    } else {
      ctk::analysis::v1::CallGraphStreamEvent event;
      event.mutable_completed()->CopyFrom(result.completed);
      if (!writer->Write(event)) {
        result.code = ctk::clang_layer::MatchCode::Cancelled;
        result.message = "call graph stream closed before completion";
      }
    }
  }
  return match_status(result.code, result.message, *context);
}
grpc::Status AnalysisServiceAdapter::StreamVariableFlow(
    grpc::ServerContext *context,
    const ctk::analysis::v1::VariableFlowRequest *request,
    grpc::ServerWriter<ctk::analysis::v1::VariableFlowEvent> *writer) {
  auto result = cfg_.variable_flow(
      *request, [context] { return !context->IsCancelled(); },
      [writer](const auto &event, std::string &message) {
        if (!writer->Write(event)) {
          message = "variable flow stream closed";
          return ctk::clang_layer::MatchCode::Cancelled;
        }
        return ctk::clang_layer::MatchCode::Ok;
      },
      owner(*context));
  return match_status(result.code, result.message, *context);
}
} // namespace ctk::net
