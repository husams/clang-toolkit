#include "ctk/application/match_controller.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <filesystem>
#include <gtest/gtest.h>
#include <optional>
#include <thread>

namespace ctk::application {
namespace {
using ctk::clang_layer::MatchCode;
using namespace ctk::match::v1;
class SnapshotOwner final : public ctk::cache::NativeSnapshotOwner {};
ctk::cache::SnapshotPtr snapshot(std::uint64_t bytes) {
  ctk::cache::LoadedSnapshot loaded;
  loaded.owner = std::make_shared<SnapshotOwner>();
  loaded.estimated_bytes = bytes;
  loaded.inputs.push_back({"/tmp/a.cc", ctk::cache::InputKind::File,
                           "revision", {}, std::nullopt});
  return std::make_shared<ctk::cache::SnapshotEntry>(
      1, "profile", std::move(loaded));
}
OpenResourceScopeRequest scope_request(std::uint64_t bytes = 64) {
  OpenResourceScopeRequest request;
  request.add_inputs()->set_file_path("/tmp/a.cc");
  request.set_memory_bytes(bytes);
  request.set_jobs(1);
  return request;
}
std::vector<ResourceInputReservation> reservations(std::uint64_t bytes = 64) {
  return {{"/tmp/a.cc\nprofile", bytes}};
}
InputDescriptor descriptor(std::string path = "/tmp/a.cc") {
  InputDescriptor input;
  input.set_file_path(std::move(path));
  input.mutable_profile()->set_profile_id("profile");
  input.mutable_profile()->set_working_directory("/tmp");
  input.mutable_profile()->set_frozen(true);
  return input;
}
class ResourceManagement : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory directory{"ctk-resources"};
  MatchController controller;
  MatchRequest file() {
    std::ofstream(directory.path() / "file.cc") << "int f() { return 3; }\n";
    MatchRequest request;
    request.set_query("functionDecl().bind(\"f\")");
    request.mutable_file()->set_file_path("file.cc");
    request.mutable_file()->set_working_directory(directory.path().string());
    return request;
  }
};

TEST_F(ResourceManagement, ListsOwnedSessionsAndAttachesWithoutChangingRevision) {
  const auto result = controller.match("alice", file(), [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok);
  const auto listed = controller.list_sessions("alice");
  ASSERT_EQ(listed.sessions_size(), 1);
  EXPECT_EQ(controller.list_sessions("bob").sessions_size(), 0);
  const auto &info = listed.sessions(0);
  EXPECT_EQ(info.session_id(), result.response.session_id());
  EXPECT_EQ(info.file_path(),
            std::filesystem::absolute(directory.path() / "file.cc")
                .lexically_normal()
                .string());
  EXPECT_EQ(info.row_count(), 1U);
  EXPECT_EQ(info.binding_names_size(), 2);
  SessionInfo attached;
  EXPECT_EQ(controller.attach_session("bob", info.session_id(), attached).code, MatchCode::NotFound);
  ASSERT_EQ(controller.attach_session("alice", info.session_id(), attached).code, MatchCode::Ok);
  EXPECT_EQ(attached.result_revision(), info.result_revision());
  EXPECT_GE(attached.expires_at().seconds(), info.expires_at().seconds());
  EXPECT_EQ(controller.attach_session("alice", "bad", attached).code, MatchCode::InvalidArgument);
  EXPECT_EQ(controller.close("alice", info.session_id()).code, MatchCode::Ok);
  EXPECT_EQ(controller.attach_session("alice", info.session_id(), attached).code, MatchCode::NotFound);
  EXPECT_EQ(controller.list_sessions("alice").sessions_size(), 0);
}

TEST_F(ResourceManagement, StatusAccountsForRetainedMemoryAndPrunePreservesCursor) {
  const auto result = controller.match("alice", file(), [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok);
  const auto status = controller.server_status();
  EXPECT_EQ(status.active_sessions(), 1U);
  EXPECT_GT(status.retained_memory_bytes(), 0U);
  EXPECT_TRUE(status.cache().memory_available());
  EXPECT_GT(status.cache().reusable_snapshots(), 0U);
  PruneCachesRequest request;
  PruneCachesResponse pruned;
  EXPECT_EQ(controller.prune_caches(request, pruned).code, MatchCode::InvalidArgument);
  request.set_memory(true);
  ASSERT_EQ(controller.prune_caches(request, pruned).code, MatchCode::Ok);
  EXPECT_EQ(pruned.after().reusable_snapshots(), 0U);
  EXPECT_EQ(controller.server_status().active_sessions(), 1U);
  MatchRequest continuation;
  continuation.set_query("integerLiteral().bind(\"n\")");
  continuation.mutable_session()->set_session_id(result.response.session_id());
  EXPECT_EQ(controller.match("alice", continuation, [] { return true; }).code, MatchCode::Ok);
}

TEST_F(ResourceManagement, ExpiredSessionsCannotBeAttachedOrListed) {
  CursorSettings settings;
  settings.idle_ttl = std::chrono::milliseconds(1);
  MatchController expiring(settings);
  const auto result = expiring.match("alice", file(), [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok);
  std::this_thread::sleep_for(std::chrono::milliseconds(2));
  SessionInfo attached;
  EXPECT_EQ(expiring.attach_session("alice", result.response.session_id(), attached).code, MatchCode::NotFound);
  EXPECT_EQ(expiring.list_sessions("alice").sessions_size(), 0);
}

TEST(ResourceScopes, AdmissionIsAtomicAndOwnerAndJobsAreEnforced) {
  ResourceManagerSettings settings;
  settings.max_memory_bytes = 100;
  settings.max_inputs = 2;
  auto manager = std::make_shared<ResourceManager>(settings);
  auto request = scope_request(100);
  ResourceScopeInfo info;
  std::string message;
  EXPECT_EQ(manager->open_scope("alice", request,
                               {{"/tmp/a.cc\nprofile", 60}}, info, message),
            MatchCode::Ok);
  ResourceManager::WorkLease work;
  ASSERT_EQ(manager->begin_work("alice", info.resource_scope_id(), work,
                               message), MatchCode::Ok);
  ResourceManager::WorkLease extra;
  EXPECT_EQ(manager->begin_work("alice", info.resource_scope_id(), extra,
                               message), MatchCode::ResourceExhausted);
  ResourceScopeInfo denied;
  EXPECT_EQ(manager->describe_scope("bob", info.resource_scope_id(), denied),
            MatchCode::NotFound);
  EXPECT_EQ(manager->cancel_scope("alice", info.resource_scope_id(), info),
            MatchCode::Ok);
  EXPECT_FALSE(work.checkpoint());
  work = {};
  EXPECT_EQ(manager->release_scope("alice", info.resource_scope_id(), info),
            MatchCode::Ok);
  EXPECT_EQ(info.state(), RESOURCE_SCOPE_STATE_RELEASED);
  EXPECT_TRUE(info.cleanup_acknowledged());
}

TEST(ResourceScopes, NativeEstimatesAreCheckedAndCleanupMustAcknowledge) {
  ResourceManagerSettings settings;
  settings.max_memory_bytes = 100;
  auto manager = std::make_shared<ResourceManager>(settings);
  auto request = scope_request(100);
  ResourceScopeInfo info;
  std::string message;
  ASSERT_EQ(manager->open_scope("alice", request, reservations(60), info,
                               message), MatchCode::Ok);
  EXPECT_THROW(manager->claim_snapshot("alice", info.resource_scope_id(),
                                      "/tmp/a.cc\nprofile", snapshot(120), {}),
               std::runtime_error);
  EXPECT_EQ(manager->release_scope("alice", info.resource_scope_id(), info),
            MatchCode::Ok);
  EXPECT_TRUE(info.cleanup_acknowledged());

  request = scope_request(100);
  ASSERT_EQ(manager->open_scope("alice", request, reservations(60), info,
                               message), MatchCode::Ok);
  std::atomic<int> attempts{0};
  manager->register_cursor("alice", info.resource_scope_id(), "retry-cursor",
                          "/tmp/a.cc\nprofile", snapshot(60), [&] {
                            return ++attempts > 1;
                          });
  ASSERT_EQ(manager->release_scope("alice", info.resource_scope_id(), info),
            MatchCode::Ok);
  EXPECT_FALSE(info.cleanup_acknowledged());
  std::this_thread::sleep_for(std::chrono::milliseconds(150));
  ASSERT_EQ(manager->describe_scope("alice", info.resource_scope_id(), info),
            MatchCode::Ok);
  EXPECT_TRUE(info.cleanup_acknowledged());
  EXPECT_EQ(attempts.load(), 2);
}

TEST(ResourceScopes, ExpiryClosesOwnedCursorAndReportsAcknowledgment) {
  ResourceManagerSettings settings;
  settings.default_ttl = std::chrono::milliseconds(200);
  settings.terminal_ttl = std::chrono::milliseconds(200);
  auto manager = std::make_shared<ResourceManager>(settings);
  auto request = scope_request(100);
  request.set_ttl_ms(40);
  ResourceScopeInfo info;
  std::string message;
  ASSERT_EQ(manager->open_scope("alice", request, reservations(60), info,
                               message), MatchCode::Ok);
  std::atomic<int> closed{0};
  manager->register_cursor("alice", info.resource_scope_id(), "cursor-id",
                          "/tmp/a.cc\nprofile", snapshot(60), [&] {
                            ++closed;
                            return true;
                          });
  std::this_thread::sleep_for(std::chrono::milliseconds(130));
  ASSERT_EQ(manager->describe_scope("alice", info.resource_scope_id(), info),
            MatchCode::Ok);
  EXPECT_EQ(info.state(), RESOURCE_SCOPE_STATE_EXPIRED);
  EXPECT_TRUE(info.cleanup_acknowledged());
  EXPECT_EQ(closed.load(), 1);
}

TEST(ResourceScopes, ClaimsCanEnrollLeasesAndUnscopedPinsRespectReservations) {
  ResourceManagerSettings settings;
  settings.max_inputs = 1;
  settings.max_memory_bytes = 100;
  auto manager = std::make_shared<ResourceManager>(settings);
  auto request = scope_request(100);
  ResourceScopeInfo info;
  std::string message;
  ASSERT_EQ(manager->open_scope("alice", request, reservations(80), info,
                                message),
            MatchCode::Ok);
  const auto scope = info.resource_scope_id();
  const auto pinned = snapshot(80);
  manager->claim_snapshot("alice", scope, "/tmp/a.cc\nprofile", pinned, {});
  EXPECT_NO_THROW(manager->register_file_lease(
      "alice", scope, "manifest-lease", "/tmp/a.cc\nprofile",
      pinned, [] { return true; }));
  EXPECT_THROW(manager->register_file_lease(
                   "bob", "", "outside-lease", "/tmp/b.cc\nprofile",
                   snapshot(30), [] { return true; }),
               std::runtime_error);
  EXPECT_EQ(manager->release_scope("alice", scope, info), MatchCode::Ok);

  ResourceManagerSettings memory_settings;
  memory_settings.max_memory_bytes = 100;
  auto memory_manager = std::make_shared<ResourceManager>(memory_settings);
  ASSERT_EQ(memory_manager->open_scope("alice", request, reservations(80),
                                       info, message),
            MatchCode::Ok);
  EXPECT_THROW(memory_manager->register_cursor(
                   "bob", "", "outside-cursor", "/tmp/b.cc\nprofile",
                   snapshot(30), [] { return true; }),
               std::runtime_error);
}

TEST(ResourceScopes, UnscopedNativeWorkAppearsInResourceStatusUntilFinished) {
  auto manager = std::make_shared<ResourceManager>(ResourceManagerSettings{});
  CursorSettings settings;
  settings.resources = manager;
  MatchController controller(settings);
  ResourceManager::WorkLease work;
  std::string message;
  ASSERT_EQ(manager->begin_work("alice", "", work, message), MatchCode::Ok);
  EXPECT_TRUE(work.checkpoint());
  const auto pinned = snapshot(80);
  manager->register_work_snapshot("alice", work.token(),
                                  "/tmp/a.cc\nprofile", pinned,
                                  descriptor());
  ctk::match::v1::CacheResources cache;
  const auto active = manager->status(cache, std::nullopt);
  EXPECT_EQ(active.active_work(), 1U);
  EXPECT_EQ(active.opened_inputs(), 1U);
  EXPECT_EQ(active.accounted_native_bytes(), 80U);
  EXPECT_EQ(manager->active_work_for("alice", "/tmp/a.cc\nprofile"), 1U);
  const auto listed = controller.list_files("alice");
  ASSERT_EQ(listed.files_size(), 1);
  EXPECT_EQ(listed.files(0).input().file_path(), "/tmp/a.cc");
  EXPECT_EQ(listed.files(0).active_work(), 1U);
  EXPECT_EQ(listed.files(0).accounted_native_bytes(), 80U);
  EXPECT_TRUE(controller.list_files("bob").files().empty());
  work = {};
  EXPECT_EQ(manager->status(cache, std::nullopt).active_work(), 0U);
  EXPECT_EQ(manager->active_work_for("alice", "/tmp/a.cc\nprofile"), 0U);
  EXPECT_TRUE(controller.list_files("alice").files().empty());
}

TEST(ResourceScopes, WorkSnapshotAdmissionEnforcesUniqueInputLimit) {
  ResourceManagerSettings settings;
  settings.max_inputs = 1;
  auto manager = std::make_shared<ResourceManager>(settings);
  ResourceManager::WorkLease first;
  ResourceManager::WorkLease second;
  std::string message;
  ASSERT_EQ(manager->begin_work("alice", "", first, message), MatchCode::Ok);
  ASSERT_EQ(manager->begin_work("alice", "", second, message), MatchCode::Ok);
  manager->register_work_snapshot("alice", first.token(),
                                  "/tmp/a.cc\nprofile", snapshot(80),
                                  descriptor());
  EXPECT_THROW(manager->register_work_snapshot(
                   "alice", second.token(), "/tmp/b.cc\nprofile",
                   snapshot(80), descriptor("/tmp/b.cc")),
               std::runtime_error);
}

TEST(ResourceScopes, DetachedScopeClaimStaysInFileInventoryUntilRelease) {
  auto manager = std::make_shared<ResourceManager>(ResourceManagerSettings{});
  CursorSettings settings;
  settings.resources = manager;
  MatchController controller(settings);
  auto request = scope_request(100);
  ResourceScopeInfo scope;
  std::string message;
  ASSERT_EQ(manager->open_scope("alice", request, reservations(100), scope,
                                message),
            MatchCode::Ok);
  ResourceManager::WorkLease work;
  ASSERT_EQ(manager->begin_work("alice", scope.resource_scope_id(), work,
                                message),
            MatchCode::Ok);
  const auto pinned = snapshot(80);
  manager->claim_snapshot("alice", scope.resource_scope_id(),
                          "/tmp/a.cc\nprofile", pinned, {}, descriptor());
  manager->register_work_snapshot("alice", work.token(),
                                  "/tmp/a.cc\nprofile", pinned,
                                  descriptor());
  work = {};
  auto listed = controller.list_files("alice");
  ASSERT_EQ(listed.files_size(), 1);
  EXPECT_EQ(listed.files(0).resource_scope_id(), scope.resource_scope_id());
  EXPECT_EQ(listed.files(0).active_work(), 0U);
  EXPECT_EQ(listed.files(0).input().profile().compile_arguments_size(), 0);
  EXPECT_TRUE(controller.list_files("bob").files().empty());
  ASSERT_EQ(manager->release_scope("alice", scope.resource_scope_id(), scope),
            MatchCode::Ok);
  EXPECT_TRUE(controller.list_files("alice").files().empty());
}
}
}
