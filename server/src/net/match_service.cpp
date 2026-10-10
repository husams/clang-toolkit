#include "ctk/net/match_service.hpp"
#include "match_status.hpp"

namespace ctk::net {
namespace {
// The configured insecure transports serve one local user's analysis session.
// If authenticated transport is supplied later, derive ownership from its
// verified identity, never from request text or caller-controlled metadata.
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
grpc::Status
MatchServiceAdapter::Parse(grpc::ServerContext *context,
                           const ctk::match::v1::ParseRequest *request,
                           ctk::match::v1::ParseResponse *response) {
  auto reply = controller_.parse(owner(*context), *request,
                                 [context] { return !context->IsCancelled(); });
  if (reply.code == ctk::clang_layer::MatchCode::Ok)
    response->Swap(&reply.response);
  return match_status(reply.code, reply.message, *context);
}
grpc::Status
MatchServiceAdapter::Match(grpc::ServerContext *context,
                           const ctk::match::v1::MatchRequest *request,
                           ctk::match::v1::MatchResponse *response) {
  auto reply = controller_.match(owner(*context), *request,
                                 [context] { return !context->IsCancelled(); });
  if (reply.code == ctk::clang_layer::MatchCode::Ok)
    response->Swap(&reply.response);
  return match_status(reply.code, reply.message, *context);
}
grpc::Status MatchServiceAdapter::StreamMatch(
    grpc::ServerContext *context, const ctk::match::v1::MatchRequest *request,
    grpc::ServerWriter<ctk::match::v1::MatchStreamEvent> *writer) {
  auto reply = controller_.stream_match(
      owner(*context), *request, [context] { return !context->IsCancelled(); },
      [context, writer](const ctk::match::v1::MatchStreamEvent &event,
                        std::string &message) {
        if (context->IsCancelled()) {
          message = "match stream cancelled";
          return ctk::clang_layer::MatchCode::Cancelled;
        }
        if (!writer->Write(event)) {
          message = "match stream consumer disconnected";
          return ctk::clang_layer::MatchCode::Cancelled;
        }
        return ctk::clang_layer::MatchCode::Ok;
      });
  return match_status(reply.code, reply.message, *context);
}
grpc::Status MatchServiceAdapter::CloseSession(
    grpc::ServerContext *context,
    const ctk::match::v1::CloseSessionRequest *request,
    ctk::match::v1::CloseSessionResponse *) {
  const auto reply = controller_.close(owner(*context), request->session_id());
  return match_status(reply.code, reply.message, *context);
}
grpc::Status MatchServiceAdapter::ListSessions(
    grpc::ServerContext *context, const ctk::match::v1::ListSessionsRequest *,
    ctk::match::v1::ListSessionsResponse *response) {
  try {
    *response = controller_.list_sessions(owner(*context));
    return grpc::Status::OK;
  } catch (const std::exception &error) {
    return grpc::Status(grpc::StatusCode::INTERNAL, error.what());
  }
}
grpc::Status MatchServiceAdapter::AttachSession(
    grpc::ServerContext *context, const ctk::match::v1::AttachSessionRequest *request,
    ctk::match::v1::SessionInfo *response) {
  const auto reply = controller_.attach_session(owner(*context), request->session_id(), *response);
  return match_status(reply.code, reply.message, *context);
}
grpc::Status MatchServiceAdapter::ServerStatus(
    grpc::ServerContext *, const ctk::match::v1::ServerStatusRequest *,
    ctk::match::v1::ServerStatusResponse *response) {
  try {
    *response = controller_.server_status();
    return grpc::Status::OK;
  } catch (const std::exception &error) {
    return grpc::Status(grpc::StatusCode::INTERNAL, error.what());
  }
}
grpc::Status MatchServiceAdapter::PruneCaches(
    grpc::ServerContext *context, const ctk::match::v1::PruneCachesRequest *request,
    ctk::match::v1::PruneCachesResponse *response) {
  const auto reply = controller_.prune_caches(*request, *response);
  return match_status(reply.code, reply.message, *context);
}
grpc::Status MatchServiceAdapter::DiscoverFiles(
    grpc::ServerContext *context, const ctk::match::v1::DiscoverFilesRequest *request,
    ctk::match::v1::DiscoverFilesResponse *response) {
  ctk::clang_layer::MatchCode code;
  std::string message;
  *response = controller_.discover_files(
      *request, [context] { return !context->IsCancelled(); }, code, message);
  return match_status(code, message, *context);
}
grpc::Status MatchServiceAdapter::OpenFile(
    grpc::ServerContext *context, const ctk::match::v1::OpenFileRequest *request,
    ctk::match::v1::FileInfo *response) {
  std::string message;
  const auto code = controller_.open_file(
      owner(*context), *request,
      [context] { return !context->IsCancelled(); }, *response, message);
  return match_status(code, message, *context);
}
grpc::Status MatchServiceAdapter::ListFiles(
    grpc::ServerContext *context, const ctk::match::v1::ListFilesRequest *,
    ctk::match::v1::ListFilesResponse *response) {
  *response = controller_.list_files(owner(*context));
  return grpc::Status::OK;
}
grpc::Status MatchServiceAdapter::DescribeFile(
    grpc::ServerContext *context, const ctk::match::v1::DescribeFileRequest *request,
    ctk::match::v1::FileInfo *response) {
  const auto code = controller_.describe_file(owner(*context), *request, *response);
  return match_status(code, {}, *context);
}
grpc::Status MatchServiceAdapter::CloseFile(
    grpc::ServerContext *context, const ctk::match::v1::CloseFileRequest *request,
    ctk::match::v1::CloseFileResponse *response) {
  const auto code = controller_.close_file(owner(*context), *request, *response);
  return match_status(code, {}, *context);
}
grpc::Status MatchServiceAdapter::CloseAllFiles(
    grpc::ServerContext *context, const ctk::match::v1::CloseAllFilesRequest *,
    ctk::match::v1::CloseFileResponse *response) {
  const auto code = controller_.close_all_files(owner(*context), *response);
  return match_status(code, {}, *context);
}
grpc::Status MatchServiceAdapter::RefreshFile(
    grpc::ServerContext *context, const ctk::match::v1::RefreshFileRequest *request,
    ctk::match::v1::FileInfo *response) {
  std::string message;
  const auto code = controller_.refresh_file(
      owner(*context), *request,
      [context] { return !context->IsCancelled(); }, *response, message);
  return match_status(code, message, *context);
}
grpc::Status MatchServiceAdapter::OpenResourceScope(
    grpc::ServerContext *context, const ctk::match::v1::OpenResourceScopeRequest *request,
    ctk::match::v1::ResourceScopeInfo *response) {
  std::string message;
  const auto code = controller_.open_resource_scope(owner(*context), *request,
                                                     *response, message);
  return match_status(code, message, *context);
}
grpc::Status MatchServiceAdapter::DescribeResourceScope(
    grpc::ServerContext *context, const ctk::match::v1::ResourceScopeRequest *request,
    ctk::match::v1::ResourceScopeInfo *response) {
  const auto code = controller_.describe_resource_scope(
      owner(*context), request->resource_scope_id(), *response);
  return match_status(code, {}, *context);
}
grpc::Status MatchServiceAdapter::CancelResourceScope(
    grpc::ServerContext *context, const ctk::match::v1::ResourceScopeRequest *request,
    ctk::match::v1::ResourceScopeInfo *response) {
  const auto code = controller_.cancel_resource_scope(
      owner(*context), request->resource_scope_id(), *response);
  return match_status(code, {}, *context);
}
grpc::Status MatchServiceAdapter::ReleaseResourceScope(
    grpc::ServerContext *context, const ctk::match::v1::ResourceScopeRequest *request,
    ctk::match::v1::ResourceScopeInfo *response) {
  const auto code = controller_.release_resource_scope(
      owner(*context), request->resource_scope_id(), *response);
  return match_status(code, {}, *context);
}
grpc::Status MatchServiceAdapter::ResourceStatus(
    grpc::ServerContext *, const ctk::match::v1::ResourceStatusRequest *,
    ctk::match::v1::ResourceStatusResponse *response) {
  *response = controller_.resource_status();
  return grpc::Status::OK;
}
} // namespace ctk::net
