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
  grpc::Status DiscoverFiles(grpc::ServerContext *,
      const ctk::match::v1::DiscoverFilesRequest *,
      ctk::match::v1::DiscoverFilesResponse *) override;
  grpc::Status OpenFile(grpc::ServerContext *,
      const ctk::match::v1::OpenFileRequest *, ctk::match::v1::FileInfo *) override;
  grpc::Status ListFiles(grpc::ServerContext *,
      const ctk::match::v1::ListFilesRequest *, ctk::match::v1::ListFilesResponse *) override;
  grpc::Status DescribeFile(grpc::ServerContext *,
      const ctk::match::v1::DescribeFileRequest *, ctk::match::v1::FileInfo *) override;
  grpc::Status CloseFile(grpc::ServerContext *,
      const ctk::match::v1::CloseFileRequest *, ctk::match::v1::CloseFileResponse *) override;
  grpc::Status CloseAllFiles(grpc::ServerContext *,
      const ctk::match::v1::CloseAllFilesRequest *, ctk::match::v1::CloseFileResponse *) override;
  grpc::Status RefreshFile(grpc::ServerContext *,
      const ctk::match::v1::RefreshFileRequest *, ctk::match::v1::FileInfo *) override;
  grpc::Status OpenResourceScope(grpc::ServerContext *,
      const ctk::match::v1::OpenResourceScopeRequest *, ctk::match::v1::ResourceScopeInfo *) override;
  grpc::Status DescribeResourceScope(grpc::ServerContext *,
      const ctk::match::v1::ResourceScopeRequest *, ctk::match::v1::ResourceScopeInfo *) override;
  grpc::Status CancelResourceScope(grpc::ServerContext *,
      const ctk::match::v1::ResourceScopeRequest *, ctk::match::v1::ResourceScopeInfo *) override;
  grpc::Status ReleaseResourceScope(grpc::ServerContext *,
      const ctk::match::v1::ResourceScopeRequest *, ctk::match::v1::ResourceScopeInfo *) override;
  grpc::Status ResourceStatus(grpc::ServerContext *,
      const ctk::match::v1::ResourceStatusRequest *, ctk::match::v1::ResourceStatusResponse *) override;

private:
  application::MatchController &controller_;
};
} // namespace ctk::net
