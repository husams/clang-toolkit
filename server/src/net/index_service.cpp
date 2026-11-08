#include "ctk/net/index_service.hpp"

#include <utility>

namespace ctk::net {
using namespace ctk::index::v1;
using application::IndexAction;

namespace {
application::IndexReadControl read_control(grpc::ServerContext &context) {
  return {context.deadline(), [&context] { return context.IsCancelled(); }};
}

template <class Function> grpc::Status rpc(Function &&function) {
#ifndef CTK_WITH_CLANG
  return {grpc::StatusCode::UNIMPLEMENTED,
          "Clang support is disabled in this server build"};
#else
  try {
    function();
    return grpc::Status::OK;
  } catch (const std::invalid_argument &e) {
    return {grpc::StatusCode::INVALID_ARGUMENT, e.what()};
  } catch (const std::logic_error &e) {
    return {grpc::StatusCode::FAILED_PRECONDITION, e.what()};
  } catch (const std::exception &e) {
    return {grpc::StatusCode::UNAVAILABLE, e.what()};
  }
#endif
}
} // namespace
IndexServiceAdapter::IndexServiceAdapter(std::filesystem::path root,
                                         std::function<bool()> foreground_busy,
                                         std::filesystem::path executable,
                                         std::size_t max_workers)
    : indexer_(
          std::move(root), std::move(foreground_busy), std::move(executable),
          max_workers) {}
IndexServiceAdapter::~IndexServiceAdapter() = default;
grpc::Status
IndexServiceAdapter::ListProjectIndexes(grpc::ServerContext *context,
                                        const ListProjectIndexesRequest *,
                                        ListProjectIndexesResponse *out) {
  // Inventory reads do not require the native extraction backend. In
  // particular, ServerStatus must remain available in builds without Clang.
  try {
    *out = indexer_.list(read_control(*context));
    return grpc::Status::OK;
  } catch (const std::exception &error) {
    return {grpc::StatusCode::UNAVAILABLE, error.what()};
  }
}
grpc::Status
IndexServiceAdapter::StartProjectIndex(grpc::ServerContext *,
                                       const StartProjectIndexRequest *request,
                                       ProjectIndexStatus *out) {
  return rpc([&] { *out = indexer_.start(*request); });
}
grpc::Status
IndexServiceAdapter::GetProjectIndexStatus(grpc::ServerContext *,
                                           const ProjectIndexRequest *request,
                                           ProjectIndexStatus *out) {
  return rpc([&] { *out = indexer_.status(request->project_root()); });
}
grpc::Status IndexServiceAdapter::RenameProjectIndex(
    grpc::ServerContext *, const RenameProjectIndexRequest *request,
    ProjectIndexStatus *out) {
  return rpc([&] { *out = indexer_.rename(*request); });
}
grpc::Status
IndexServiceAdapter::PauseProjectIndex(grpc::ServerContext *,
                                       const ProjectIndexRequest *request,
                                       ProjectIndexStatus *out) {
  return rpc([&] { *out = indexer_.control(request->project_root(), IndexAction::Pause); });
}
grpc::Status
IndexServiceAdapter::ResumeProjectIndex(grpc::ServerContext *,
                                        const ProjectIndexRequest *request,
                                        ProjectIndexStatus *out) {
  return rpc([&] { *out = indexer_.control(request->project_root(), IndexAction::Resume); });
}
grpc::Status
IndexServiceAdapter::CancelProjectIndex(grpc::ServerContext *,
                                        const ProjectIndexRequest *request,
                                        ProjectIndexStatus *out) {
  return rpc([&] { *out = indexer_.control(request->project_root(), IndexAction::Cancel); });
}
grpc::Status IndexServiceAdapter::FindSymbols(grpc::ServerContext *context,
                                              const FindSymbolsRequest *request,
                                              FindSymbolsResponse *out) {
  return rpc([&] { *out = indexer_.find(*request, read_control(*context)); });
}
grpc::Status
IndexServiceAdapter::LookupSymbol(grpc::ServerContext *context,
                                  const LookupSymbolRequest *request,
                                  FindSymbolsResponse *out) {
  return rpc([&] { *out = indexer_.lookup(*request, read_control(*context)); });
}
} // namespace ctk::net
