#pragma once

#include "analysis/v1/batch.pb.h"
#include "ctk/application/resource_manager.hpp"
#include "ctk/application/script_controller.hpp"

#include <filesystem>
#include <functional>
#include <memory>
#include <string>
#include <string_view>

namespace ctk::application {

struct BatchRegistryLimits {
  std::size_t max_active_runs{64};
  std::size_t max_manifests{256};
  std::uint64_t max_persisted_bytes{256ULL * 1024 * 1024};
  std::uint64_t max_manifest_bytes{2ULL * 1024 * 1024};
  std::uint64_t max_result_bytes{1024ULL * 1024};
  std::uint64_t max_result_items{10000};
  std::uint32_t max_inputs{10000};
  std::uint32_t max_group_size{100};
  std::uint32_t max_groups{10000};
  std::uint32_t max_jobs{3};
  std::uint64_t max_memory_bytes{2ULL * 1024 * 1024 * 1024};
  // Optional persistence seam for deterministic journal failure tests.
  std::function<void(const std::filesystem::path &, std::string_view)>
      journal_write;
};

// Owns durable batch manifests and the single background worker that executes
// one independently admitted native script scope per group.
class BatchRegistry final {
public:
  BatchRegistry(ScriptController &scripts,
                std::shared_ptr<ResourceManager> resources,
                std::filesystem::path storage_root,
                BatchRegistryLimits limits = {});
  ~BatchRegistry();
  BatchRegistry(const BatchRegistry &) = delete;
  BatchRegistry &operator=(const BatchRegistry &) = delete;

  ctk::clang_layer::MatchCode
  start(const ctk::analysis::v1::StartBatchRequest &request,
        const std::string &owner, ctk::analysis::v1::BatchRun &response,
        std::string &message);
  ctk::clang_layer::MatchCode
  status(const ctk::analysis::v1::BatchRunRequest &request,
         const std::string &owner, ctk::analysis::v1::BatchRun &response,
         std::string &message) const;
  ctk::clang_layer::MatchCode
  cancel(const ctk::analysis::v1::BatchControlRequest &request,
         const std::string &owner, ctk::analysis::v1::BatchRun &response,
         std::string &message);
  ctk::clang_layer::MatchCode
  resume(const ctk::analysis::v1::BatchControlRequest &request,
         const std::string &owner, ctk::analysis::v1::BatchRun &response,
         std::string &message);
  ctk::clang_layer::MatchCode
  retry(const ctk::analysis::v1::BatchControlRequest &request,
        const std::string &owner, ctk::analysis::v1::BatchRun &response,
        std::string &message);
  void shutdown();

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

} // namespace ctk::application
