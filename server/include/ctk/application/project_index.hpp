#pragma once

#include "index/v1/index_service.pb.h"

#include <chrono>
#include <filesystem>
#include <functional>
#include <memory>

namespace ctk::application {

struct IndexReadControl {
  std::chrono::system_clock::time_point deadline =
      std::chrono::system_clock::time_point::max();
  std::function<bool()> cancelled;

  bool interrupted() const {
    return (cancelled && cancelled()) ||
           std::chrono::system_clock::now() >= deadline;
  }
};

enum class IndexAction { Pause, Resume, Cancel };

class ProjectIndexController final {
public:
  explicit ProjectIndexController(std::filesystem::path storage_root,
                                  std::function<bool()> foreground_busy = {},
                                  std::filesystem::path worker_executable = {},
                                  std::size_t max_workers = 0);
  ~ProjectIndexController();

  index::v1::ListProjectIndexesResponse
  list(const IndexReadControl &control = {});
  index::v1::ProjectIndexStatus
  start(const index::v1::StartProjectIndexRequest &request);
  index::v1::ProjectIndexStatus
  rename(const index::v1::RenameProjectIndexRequest &request);
  index::v1::ProjectIndexStatus status(const std::string &root);
  index::v1::ProjectIndexStatus control(const std::string &root,
                                       IndexAction action);
  index::v1::FindSymbolsResponse find(const index::v1::FindSymbolsRequest &request,
                                      const IndexReadControl &control = {});
  index::v1::FindSymbolsResponse lookup(const index::v1::LookupSymbolRequest &request,
                                        const IndexReadControl &control = {});

private:
  class Impl;
  std::unique_ptr<Impl> impl_;
};

} // namespace ctk::application
