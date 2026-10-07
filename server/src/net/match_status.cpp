#include "match_status.hpp"

namespace ctk::net {
grpc::Status match_status(ctk::clang_layer::MatchCode result,
                          const std::string &message,
                          grpc::ServerContext &context) {
  using ctk::clang_layer::MatchCode;
  grpc::StatusCode code;
  switch (result) {
  case MatchCode::Ok:
    return grpc::Status::OK;
  case MatchCode::InvalidArgument:
    code = grpc::StatusCode::INVALID_ARGUMENT;
    break;
  case MatchCode::NotFound:
    code = grpc::StatusCode::NOT_FOUND;
    break;
  case MatchCode::FailedPrecondition:
    code = grpc::StatusCode::FAILED_PRECONDITION;
    break;
  case MatchCode::ResourceExhausted:
    code = grpc::StatusCode::RESOURCE_EXHAUSTED;
    break;
  case MatchCode::Aborted:
    code = grpc::StatusCode::ABORTED;
    break;
  case MatchCode::Cancelled:
    code = std::chrono::system_clock::now() >= context.deadline()
               ? grpc::StatusCode::DEADLINE_EXCEEDED
               : grpc::StatusCode::CANCELLED;
    break;
  case MatchCode::Internal:
    code = grpc::StatusCode::INTERNAL;
    break;
  }
  return {code, message};
}
} // namespace ctk::net
