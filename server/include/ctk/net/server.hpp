#pragma once

#include "ctk/config/config.hpp"
#include "ctk/net/analysis_service.hpp"
#include "ctk/net/match_service.hpp"
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
  std::shared_ptr<application::OperationExecutor> operations_;
  std::shared_ptr<ctk::clang_layer::IQueryEngine> native_engine_;
  std::shared_ptr<application::ResourceManager> resources_;
  application::MatchController matches_;
  MatchServiceAdapter match_service_;
  application::TraversalController traversals_;
  application::CfgController cfg_;
  application::CallGraphController calls_;
  application::ScriptController scripts_;
  application::BatchRegistry batches_;
  AnalysisServiceAdapter analysis_service_;
  std::unique_ptr<platform::EndpointLease> lease_;
  std::unique_ptr<grpc::Server> server_;
};

} // namespace ctk::net
