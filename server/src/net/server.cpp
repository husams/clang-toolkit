#include "ctk/net/server.hpp"
#include "ctk/clang/tooling.hpp"

#include <algorithm>
#include <chrono>
#include <grpcpp/security/server_credentials.h>
#include <grpcpp/server_builder.h>
#include <limits>
#include <stdexcept>

namespace ctk::net {

namespace {
std::shared_ptr<ctk::clang_layer::IQueryEngine> native_engine() {
#ifdef CTK_WITH_CLANG
  return ctk::clang_layer::make_query_engine();
#else
  return {};
#endif
}
std::shared_ptr<ctk::clang_layer::IMatchBackend>
matcher(std::shared_ptr<ctk::clang_layer::IQueryEngine> engine) {
#ifdef CTK_WITH_CLANG
  return ctk::clang_layer::make_match_backend(std::move(engine));
#else
  return {};
#endif
}
std::shared_ptr<ctk::clang_layer::ITraversalBackend>
visitor(std::shared_ptr<ctk::clang_layer::IQueryEngine> engine) {
#ifdef CTK_WITH_CLANG
  return ctk::clang_layer::make_traversal_backend(std::move(engine));
#else
  return {};
#endif
}
std::shared_ptr<ctk::clang_layer::ICfgBackend>
cfg_backend(std::shared_ptr<ctk::clang_layer::IQueryEngine> engine) {
#ifdef CTK_WITH_CLANG
  return ctk::clang_layer::make_cfg_backend(std::move(engine));
#else
  return {};
#endif
}
std::shared_ptr<ctk::clang_layer::ICallGraphBackend>
calls_backend(std::shared_ptr<ctk::clang_layer::IQueryEngine> engine) {
#ifdef CTK_WITH_CLANG
  return ctk::clang_layer::make_call_graph_backend(std::move(engine));
#else
  return {};
#endif
}
application::CursorSettings cursor_settings(const config::Settings &settings) {
  application::CursorSettings result;
  result.workers = static_cast<std::size_t>(settings.pool_size);
  result.pending_requests = static_cast<std::size_t>(settings.queue_size);
  result.max_cursors = static_cast<std::size_t>(settings.max_files);
  result.max_memory_bytes =
      static_cast<std::uint64_t>(settings.max_memory_bytes);
  result.results.max_bytes = static_cast<std::size_t>(std::min<std::uint64_t>(
      result.max_memory_bytes, std::numeric_limits<int>::max()));
  // Reject oversized responses before publishing a new cursor revision.
  if (const auto configured = settings.server_grpc.max_send_message_bytes;
      configured && *configured > 0)
    result.results.max_bytes = std::min(result.results.max_bytes,
                                        static_cast<std::size_t>(*configured));
  return result;
}
} // namespace

GrpcServerHost::GrpcServerHost(config::Settings settings,
                               application::IQueryController &controller)
    : settings_(std::move(settings)), controller_(controller),
      service_(controller), operations_(application::make_operation_executor(
                                settings_.pool_size, settings_.queue_size)),
      native_engine_(native_engine()),
      matches_(cursor_settings(settings_), matcher(native_engine_),
               operations_),
      match_service_(matches_),
      traversals_(cursor_settings(settings_), visitor(native_engine_),
                  operations_),
      cfg_(cursor_settings(settings_), cfg_backend(native_engine_),
           operations_),
      calls_(cursor_settings(settings_), calls_backend(native_engine_),
             operations_),
      scripts_(cursor_settings(settings_), native_engine_, operations_),
      analysis_service_(traversals_, cfg_, calls_, scripts_) {}
GrpcServerHost::~GrpcServerHost() {
  if (server_)
    shutdown();
}
void GrpcServerHost::start() {
  if (server_)
    throw std::logic_error("server already started");
  auto lease = std::make_unique<platform::EndpointLease>(settings_.endpoint);
  grpc::ServerBuilder builder;
  if (settings_.server_grpc.max_receive_message_bytes)
    builder.SetMaxReceiveMessageSize(
        *settings_.server_grpc.max_receive_message_bytes);
  if (settings_.server_grpc.max_send_message_bytes)
    builder.SetMaxSendMessageSize(
        *settings_.server_grpc.max_send_message_bytes);
  builder.RegisterService(&service_);
  builder.RegisterService(&match_service_);
  builder.RegisterService(&analysis_service_);
  builder.AddListeningPort(settings_.endpoint,
                           grpc::InsecureServerCredentials());
  server_ = builder.BuildAndStart();
  if (!server_)
    throw std::runtime_error("gRPC could not bind " + settings_.endpoint);
  lease_ = std::move(lease);
}
void GrpcServerHost::shutdown() {
  if (!server_)
    return;
  controller_.stop_admission();
  matches_.stop_admission();
  traversals_.stop_admission();
  if (settings_.shutdown_grace_ms)
    server_->Shutdown(std::chrono::system_clock::now() +
                      std::chrono::milliseconds(*settings_.shutdown_grace_ms));
  else
    server_->Shutdown();
  server_->Wait();
  server_.reset();
  lease_.reset();
}
void GrpcServerHost::wait() {
  if (server_)
    server_->Wait();
}

} // namespace ctk::net
