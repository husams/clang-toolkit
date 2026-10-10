#pragma once

#include "ctk/cache/snapshot.hpp"
#include "ctk/clang/matching.hpp"
#include "match/v1/resources.pb.h"

#include <chrono>
#include <condition_variable>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace ctk::application {

struct ResourceManagerSettings {
  std::uint64_t max_inputs{100};
  std::uint64_t max_memory_bytes{2147483648ULL};
  std::uint32_t max_jobs{3};
  std::size_t max_scopes{128};
  std::chrono::milliseconds default_ttl{300000};
  std::chrono::milliseconds terminal_ttl{300000};
};

struct ResourceInputReservation {
  std::string identity;
  std::uint64_t estimated_bytes{0};
};

struct ResourceInputPin {
  std::string input_identity;
  std::string resource_scope_id;
  ctk::match::v1::InputDescriptor input;
  ctk::cache::SnapshotPtr snapshot;
  std::uint64_t active_work{0};
};

class ResourceManager final
    : public std::enable_shared_from_this<ResourceManager> {
public:
  class WorkLease final {
  public:
    WorkLease() = default;
    WorkLease(const WorkLease &) = delete;
    WorkLease &operator=(const WorkLease &) = delete;
    WorkLease(WorkLease &&other) noexcept;
    WorkLease &operator=(WorkLease &&other) noexcept;
    ~WorkLease();
    bool checkpoint() const;
    const std::string &token() const noexcept { return id_; }
    explicit operator bool() const noexcept { return manager_ != nullptr; }

  private:
    friend class ResourceManager;
    WorkLease(std::shared_ptr<ResourceManager> manager, std::string id,
              std::string owner);
    void reset() noexcept;
    std::shared_ptr<ResourceManager> manager_;
    std::string id_;
    std::string owner_;
  };

  explicit ResourceManager(ResourceManagerSettings settings);
  ~ResourceManager();
  ResourceManager(const ResourceManager &) = delete;
  ResourceManager &operator=(const ResourceManager &) = delete;

  ctk::clang_layer::MatchCode open_scope(
      const std::string &owner,
      const ctk::match::v1::OpenResourceScopeRequest &request,
      const std::vector<ResourceInputReservation> &inputs,
      ctk::match::v1::ResourceScopeInfo &response, std::string &message);
  ctk::clang_layer::MatchCode begin_work(const std::string &owner,
                                         const std::string &scope_id,
                                         WorkLease &lease,
                                         std::string &message);
  bool scope_transient(const std::string &owner,
                       const std::string &scope_id) const;
  ctk::clang_layer::MatchCode describe_scope(
      const std::string &owner, const std::string &scope_id,
      ctk::match::v1::ResourceScopeInfo &response);
  ctk::clang_layer::MatchCode cancel_scope(
      const std::string &owner, const std::string &scope_id,
      ctk::match::v1::ResourceScopeInfo &response);
  ctk::clang_layer::MatchCode release_scope(
      const std::string &owner, const std::string &scope_id,
      ctk::match::v1::ResourceScopeInfo &response);
  void register_cursor(const std::string &owner, const std::string &scope_id,
                      const std::string &cursor_id,
                      const std::string &input_identity,
                      ctk::cache::SnapshotPtr snapshot,
                      std::function<bool()> close,
                      std::uint64_t result_bytes = 0);
  void register_file_lease(const std::string &owner,
                           const std::string &scope_id,
                           const std::string &lease_id,
                           const std::string &input_identity,
                           ctk::cache::SnapshotPtr snapshot,
                           std::function<bool()> close);
  void claim_snapshot(const std::string &owner, const std::string &scope_id,
                      const std::string &input_identity,
                      ctk::cache::SnapshotPtr snapshot,
                      std::function<void()> release_reuse,
                      ctk::match::v1::InputDescriptor input = {});
  void unregister_cursor(const std::string &scope_id,
                         const std::string &cursor_id);
  void touch_cursor(const std::string &scope_id,
                    const std::string &cursor_id,
                    std::uint64_t result_bytes);
  void unregister_file_lease(const std::string &scope_id,
                             const std::string &lease_id);
  void register_work_snapshot(const std::string &owner,
                              const std::string &work_token,
                              const std::string &input_identity,
                              ctk::cache::SnapshotPtr snapshot,
                              ctk::match::v1::InputDescriptor input = {});
  std::uint64_t active_work_for(const std::string &owner,
                                const std::string &input_identity) const;
  std::vector<ResourceInputPin> input_pins(const std::string &owner) const;
  ctk::match::v1::ResourceStatusResponse status(
      const ctk::match::v1::CacheResources &cache,
      std::optional<std::uint64_t> resident_bytes) const;

private:
  struct Impl;
  void finish_work(const std::string &owner,
                   const std::string &scope_id) noexcept;
  bool checkpoint(const std::string &owner,
                  const std::string &scope_id) const;
  std::unique_ptr<Impl> impl_;
};

} // namespace ctk::application
