#pragma once

#include "ctk/config/config.hpp"
#include "ctk/net/network_service.hpp"
#include "ctk/platform/endpoint_lease.hpp"
#include <grpcpp/server.h>
#include <memory>

namespace ctk::net {

// gRPC exclusively owns listening sockets and their transport lifecycle.
class GrpcServerHost {
public:
  GrpcServerHost(config::Settings settings,
                 application::IQueryController &controller);
  ~GrpcServerHost();
  void start();
  void shutdown();
  void wait();
  const std::string &endpoint() const { return settings_.endpoint; }

private:
  config::Settings settings_;
  application::IQueryController &controller_;
  NetworkServiceAdapter service_;
  std::unique_ptr<platform::EndpointLease> lease_;
  std::unique_ptr<grpc::Server> server_;
};

} // namespace ctk::net
