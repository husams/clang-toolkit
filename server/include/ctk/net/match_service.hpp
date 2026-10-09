#pragma once

#include "ctk/application/match_controller.hpp"
#include "match/v1/match_service.grpc.pb.h"

namespace ctk::net {
class MatchServiceAdapter final : public ctk::match::v1::MatchService::Service {
public:
  explicit MatchServiceAdapter(application::MatchController &controller)
      : controller_(controller) {}
  grpc::Status Parse(grpc::ServerContext *,
                     const ctk::match::v1::ParseRequest *,
                     ctk::match::v1::ParseResponse *) override;
  grpc::Status Match(grpc::ServerContext *,
                     const ctk::match::v1::MatchRequest *,
                     ctk::match::v1::MatchResponse *) override;
  grpc::Status
  StreamMatch(grpc::ServerContext *, const ctk::match::v1::MatchRequest *,
              grpc::ServerWriter<ctk::match::v1::MatchStreamEvent> *) override;
  grpc::Status CloseSession(grpc::ServerContext *,
                            const ctk::match::v1::CloseSessionRequest *,
                            ctk::match::v1::CloseSessionResponse *) override;
  grpc::Status ListSessions(grpc::ServerContext *,
                           const ctk::match::v1::ListSessionsRequest *,
                           ctk::match::v1::ListSessionsResponse *) override;
  grpc::Status AttachSession(grpc::ServerContext *,
                            const ctk::match::v1::AttachSessionRequest *,
                            ctk::match::v1::SessionInfo *) override;
  grpc::Status ServerStatus(grpc::ServerContext *,
                           const ctk::match::v1::ServerStatusRequest *,
                           ctk::match::v1::ServerStatusResponse *) override;
  grpc::Status PruneCaches(grpc::ServerContext *,
                          const ctk::match::v1::PruneCachesRequest *,
                          ctk::match::v1::PruneCachesResponse *) override;

private:
  application::MatchController &controller_;
};
} // namespace ctk::net
