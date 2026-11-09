#pragma once

#include "index/v1/index_service.grpc.pb.h"
#include <cstddef>
#include <filesystem>
#include <functional>
#include <memory>

namespace ctk::net {

class BackgroundSymbolIndexer;

class IndexServiceAdapter final : public ctk::index::v1::IndexService::Service {
public:
  explicit IndexServiceAdapter(std::filesystem::path storage_root,
                               std::function<bool()> foreground_busy = {},
                               std::filesystem::path worker_executable = {},
                               std::size_t max_workers = 0);
  ~IndexServiceAdapter() override;
  grpc::Status
  ListProjectIndexes(grpc::ServerContext *,
                     const ctk::index::v1::ListProjectIndexesRequest *,
                     ctk::index::v1::ListProjectIndexesResponse *) override;
  grpc::Status
  StartProjectIndex(grpc::ServerContext *,
                    const ctk::index::v1::StartProjectIndexRequest *,
                    ctk::index::v1::ProjectIndexStatus *) override;
  grpc::Status
  RenameProjectIndex(grpc::ServerContext *,
                     const ctk::index::v1::RenameProjectIndexRequest *,
                     ctk::index::v1::ProjectIndexStatus *) override;
  grpc::Status
  GetProjectIndexStatus(grpc::ServerContext *,
                        const ctk::index::v1::ProjectIndexRequest *,
                        ctk::index::v1::ProjectIndexStatus *) override;
  grpc::Status PauseProjectIndex(grpc::ServerContext *,
                                 const ctk::index::v1::ProjectIndexRequest *,
                                 ctk::index::v1::ProjectIndexStatus *) override;
  grpc::Status
  ResumeProjectIndex(grpc::ServerContext *,
                     const ctk::index::v1::ProjectIndexRequest *,
                     ctk::index::v1::ProjectIndexStatus *) override;
  grpc::Status
  CancelProjectIndex(grpc::ServerContext *,
                     const ctk::index::v1::ProjectIndexRequest *,
                     ctk::index::v1::ProjectIndexStatus *) override;
  grpc::Status FindSymbols(grpc::ServerContext *,
                           const ctk::index::v1::FindSymbolsRequest *,
                           ctk::index::v1::FindSymbolsResponse *) override;
  grpc::Status LookupSymbol(grpc::ServerContext *,
                            const ctk::index::v1::LookupSymbolRequest *,
                            ctk::index::v1::FindSymbolsResponse *) override;

private:
  std::shared_ptr<BackgroundSymbolIndexer> indexer_;
};

} // namespace ctk::net
