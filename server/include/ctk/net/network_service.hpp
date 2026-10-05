#pragma once
#include "ctk/application/query.hpp"
#include "query/v1/query.grpc.pb.h"

namespace ctk::net {
class NetworkServiceAdapter final
    : public query::v1::QueryService::CallbackService {
public:
  explicit NetworkServiceAdapter(application::IQueryController &controller)
      : controller_(controller) {}
  grpc::ServerWriteReactor<query::v1::QueryEvent> *
  Query(grpc::CallbackServerContext *,
        const query::v1::QueryRequest *) override;
  grpc::ServerBidiReactor<query::v1::QueryCommand, query::v1::QueryEvent> *
  QuerySession(grpc::CallbackServerContext *) override;

private:
  application::IQueryController &controller_;
};
} // namespace ctk::net
