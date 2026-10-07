#pragma once
#include "ctk/clang/matching.hpp"
#include <grpcpp/server_context.h>
#include <grpcpp/support/status.h>

namespace ctk::net {
grpc::Status match_status(ctk::clang_layer::MatchCode code,
                          const std::string &message,
                          grpc::ServerContext &context);
} // namespace ctk::net
