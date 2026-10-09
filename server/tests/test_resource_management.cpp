#include "ctk/application/match_controller.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <gtest/gtest.h>
#include <thread>

namespace ctk::application {
namespace {
using ctk::clang_layer::MatchCode;
using namespace ctk::match::v1;
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
  EXPECT_EQ(info.file_path(), (directory.path() / "file.cc").string());
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
}
}
