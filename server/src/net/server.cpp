#include "ctk/net/server.hpp"

#include <chrono>
#include <grpcpp/security/server_credentials.h>
#include <grpcpp/server_builder.h>
#include <stdexcept>

namespace ctk::net {

GrpcServerHost::GrpcServerHost(config::Settings settings,
                               application::IQueryController &controller)
    : settings_(std::move(settings)), controller_(controller),
      service_(controller) {}
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
