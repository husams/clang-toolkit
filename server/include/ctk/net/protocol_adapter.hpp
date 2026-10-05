#pragma once
#include "ctk/application/query.hpp"
#include "query/v1/query.pb.h"
#include <grpcpp/support/status.h>

namespace ctk::net {
class RequestDecoder {
public:
  static application::QueryRequest
  decode_query(const query::v1::QueryRequest &);
  static application::QueryCommand
  decode_command(const query::v1::QueryCommand &);
};
class EventEncoder {
public:
  static query::v1::QueryEvent encode(const application::QueryEvent &);
};
class GrpcStatusMapper {
public:
  static grpc::Status map(const application::Outcome &);
};
} // namespace ctk::net
