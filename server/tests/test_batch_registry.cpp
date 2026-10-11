#include "ctk/application/batch_registry.hpp"

#include "ctk/clang/file_discovery.hpp"
#include "ctk/platform/durable_file.hpp"

#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <thread>

namespace ctk::application {
namespace {
using Code = ctk::clang_layer::MatchCode;

std::filesystem::path fresh_directory() {
  auto path =
      std::filesystem::temp_directory_path() /
      ("ctk-batch-registry-" +
       std::to_string(
           std::chrono::steady_clock::now().time_since_epoch().count()));
  std::filesystem::create_directories(path);
  return path;
}

TEST(DurableFile, CreatesNestedParentsAndAcceptsRelativeTargets) {
  const auto root = fresh_directory();
  const auto nested = root / "nested" / "deeper" / "manifest.pb";
  ctk::platform::durable_atomic_write(nested, "nested-bytes");
  std::ifstream nested_file(nested, std::ios::binary);
  const std::string nested_contents(
      (std::istreambuf_iterator<char>(nested_file)), {});
  EXPECT_EQ(nested_contents, "nested-bytes");

  {
    struct RestoreWorkingDirectory {
      std::filesystem::path previous = std::filesystem::current_path();
      ~RestoreWorkingDirectory() {
        std::error_code ignored;
        std::filesystem::current_path(previous, ignored);
      }
    } restore;
    std::filesystem::current_path(root);
    ctk::platform::durable_atomic_write("relative.pb", "relative-bytes");
    std::ifstream relative_file(root / "relative.pb", std::ios::binary);
    const std::string relative_contents(
        (std::istreambuf_iterator<char>(relative_file)), {});
    EXPECT_EQ(relative_contents, "relative-bytes");
  }
  std::filesystem::remove_all(root);
}

TEST(DurableFile, FailedReplacementPreservesExistingFilesAndCleansOwnedTemp) {
  const auto root = fresh_directory();
  const auto destination = root / "directory";
  std::filesystem::create_directory(destination);
  std::ofstream(destination / "existing.txt") << "preserve-directory";
  const auto sibling = root / "directory.tmp-existing";
  std::ofstream(sibling) << "preserve-other-writer";

  EXPECT_THROW(ctk::platform::durable_atomic_write(destination, "replacement"),
               std::filesystem::filesystem_error);

  EXPECT_TRUE(std::filesystem::is_directory(destination));
  std::ifstream existing(destination / "existing.txt");
  EXPECT_EQ(std::string((std::istreambuf_iterator<char>(existing)), {}),
            "preserve-directory");
  std::ifstream other(sibling);
  EXPECT_EQ(std::string((std::istreambuf_iterator<char>(other)), {}),
            "preserve-other-writer");
  EXPECT_EQ(std::distance(std::filesystem::directory_iterator(root),
                          std::filesystem::directory_iterator()),
            2);
  std::filesystem::remove_all(root);
}

ctk::match::v1::InputDescriptor
discover_one(const std::filesystem::path &root) {
  std::ofstream(root / "fixture.cpp") << "int f() { return 5; }\n";
  ctk::match::v1::DiscoverFilesRequest request;
  request.add_paths((root / "fixture.cpp").string());
  request.mutable_profile()->set_working_directory(root.string());
  auto discovered = ctk::clang_layer::discover_file_descriptors(request);
  if (discovered.inputs_size() != 1)
    throw std::runtime_error(
        "test fixture did not produce one frozen descriptor");
  return discovered.inputs(0);
}

class BlockingQueryEngine final : public ctk::clang_layer::IQueryEngine {
public:
  BlockingQueryEngine() : inner_(ctk::clang_layer::make_query_engine()) {}

  void arm() {
    std::lock_guard lock(mutex_);
    blocked_ = true;
    released_ = false;
    acquisitions_ = 0;
  }

  bool wait_for_acquisitions(int count) {
    std::unique_lock lock(mutex_);
    return changed_.wait_for(lock, std::chrono::seconds(20),
                             [&] { return acquisitions_ >= count; });
  }

  void release() {
    std::lock_guard lock(mutex_);
    released_ = true;
    blocked_ = false;
    changed_.notify_all();
  }

  ctk::cache::SnapshotPtr
  acquire_snapshot(const ctk::clang_layer::FileInput &input) override {
    {
      std::unique_lock lock(mutex_);
      if (blocked_) {
        ++acquisitions_;
        changed_.notify_all();
        changed_.wait(lock, [&] { return released_; });
      }
    }
    return inner_->acquire_snapshot(input);
  }

  ctk::clang_layer::QueryResult match(const ctk::clang_layer::FileInput &input,
                                      const std::string &query,
                                      const Checkpoint &checkpoint,
                                      const MatchCallback &on_match) override {
    return inner_->match(input, query, checkpoint, on_match);
  }

  ctk::match::v1::CacheResources resources() const override {
    return inner_->resources();
  }

  void prune_caches(bool snapshots, bool storage) override {
    inner_->prune_caches(snapshots, storage);
  }

private:
  std::shared_ptr<ctk::clang_layer::IQueryEngine> inner_;
  std::mutex mutex_;
  std::condition_variable changed_;
  bool blocked_{false};
  bool released_{false};
  int acquisitions_{0};
};

TEST(ResourceManager, InputIdentityIncludesFrozenProfileContext) {
  ctk::match::v1::InputDescriptor frozen;
  frozen.set_file_path("/tmp/fixture.cpp");
  frozen.mutable_profile()->set_frozen(true);
  frozen.mutable_profile()->set_profile_id("profile");
  frozen.mutable_profile()->set_working_directory("/tmp");
  auto mutable_profile = frozen;
  mutable_profile.mutable_profile()->set_frozen(false);

  EXPECT_NE(input_identity(frozen), input_identity(mutable_profile));
}

ctk::analysis::v1::BatchRun wait_for_completion(BatchRegistry &registry,
                                                const std::string &run_id,
                                                const std::string &owner) {
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(20);
  ctk::analysis::v1::BatchRunRequest request;
  request.set_run_id(run_id);
  while (std::chrono::steady_clock::now() < deadline) {
    ctk::analysis::v1::BatchRun response;
    std::string message;
    EXPECT_EQ(registry.status(request, owner, response, message), Code::Ok)
        << message;
    if (response.state() == "completed" || response.state() == "failed" ||
        response.state() == "interrupted")
      return response;
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  ADD_FAILURE() << "durable batch did not reach a terminal state";
  return {};
}

} // namespace

#ifdef CTK_WITH_CLANG
TEST(BatchRegistry, PersistsOwnerGuardIdempotencyRevisionAndExports) {
  const auto root = fresh_directory();
  const auto input = discover_one(root);
  auto resources = std::make_shared<ResourceManager>(ResourceManagerSettings{});
  CursorSettings settings;
  settings.workers = 1;
  settings.max_memory_bytes = 128 * 1024 * 1024;
  settings.resources = resources;
  ScriptController scripts(settings);
  const auto export_path = (root / "group.json").string();
  ctk::analysis::v1::StartBatchRequest request;
  request.set_request_id("request-1");
  *request.add_inputs() = input;
  request.set_body_source("let value = $part.index; save $value to \"" +
                          export_path + "\" as json; emit $value;");
  request.set_group_variable("part");
  request.set_size(1);
  request.set_jobs(1);

  std::string run_id;
  {
    BatchRegistry registry(scripts, resources, root);
    ctk::analysis::v1::BatchRun started;
    std::string message;
    ASSERT_EQ(registry.start(request, "owner-a", started, message), Code::Ok)
        << message;
    EXPECT_FALSE(started.results_complete());
    run_id = started.run_id();
    auto duplicate = started;
    ASSERT_EQ(registry.start(request, "owner-a", duplicate, message), Code::Ok)
        << message;
    EXPECT_EQ(duplicate.run_id(), run_id);
    auto changed = request;
    changed.set_body_source("emit 8;");
    EXPECT_EQ(registry.start(changed, "owner-a", duplicate, message),
              Code::FailedPrecondition);
    ctk::analysis::v1::BatchRunRequest lookup;
    lookup.set_run_id(run_id);
    EXPECT_EQ(registry.status(lookup, "owner-b", duplicate, message),
              Code::NotFound);

    const auto completed = wait_for_completion(registry, run_id, "owner-a");
    ASSERT_EQ(completed.state(), "completed") << completed.DebugString();
    ASSERT_EQ(completed.groups_size(), 1);
    ASSERT_TRUE(completed.groups(0).cleanup_acknowledged());
    ASSERT_GE(completed.groups(0).result().emissions_size(), 1);
    EXPECT_EQ(
        completed.groups(0).result().emissions(0).value().scalar().integer(),
        1);
    ASSERT_EQ(completed.groups(0).exports_size(), 1);
    EXPECT_EQ(completed.groups(0).exports(0).state(), "committed");
    std::ifstream export_file(export_path);
    const std::string json((std::istreambuf_iterator<char>(export_file)), {});
    EXPECT_NE(json.find("integer"), std::string::npos);

    ctk::analysis::v1::BatchControlRequest stale;
    stale.set_run_id(run_id);
    stale.set_expected_revision(started.revision());
    EXPECT_EQ(registry.cancel(stale, "owner-a", duplicate, message),
              Code::Aborted);
  }

  {
    BatchRegistry recovered(scripts, resources, root);
    ctk::analysis::v1::BatchRunRequest lookup;
    lookup.set_run_id(run_id);
    ctk::analysis::v1::BatchRun response;
    std::string message;
    ASSERT_EQ(recovered.status(lookup, "owner-a", response, message), Code::Ok)
        << message;
    EXPECT_EQ(response.state(), "completed");

    auto manifest_path = std::filesystem::path{};
    for (const auto &entry :
         std::filesystem::recursive_directory_iterator(root / "batches"))
      if (entry.is_regular_file() && entry.path().stem() == run_id)
        manifest_path = entry.path();
    ASSERT_FALSE(manifest_path.empty());
    auto interrupted = response;
    interrupted.set_state("running");
    auto *group = interrupted.mutable_groups(0);
    group->set_state("running");
    group->set_cleanup_acknowledged(false);
    ctk::platform::durable_atomic_write(manifest_path,
                                        interrupted.SerializeAsString());
  }

  {
    BatchRegistry recovered(scripts, resources, root);
    ctk::analysis::v1::BatchRunRequest lookup;
    lookup.set_run_id(run_id);
    ctk::analysis::v1::BatchRun response;
    std::string message;
    ASSERT_EQ(recovered.status(lookup, "owner-a", response, message), Code::Ok)
        << message;
    EXPECT_EQ(response.state(), "interrupted");
    ASSERT_EQ(response.groups_size(), 1);
    EXPECT_EQ(response.groups(0).state(), "unknown");
    ctk::analysis::v1::BatchControlRequest resume;
    resume.set_run_id(run_id);
    resume.set_expected_revision(response.revision());
    EXPECT_EQ(recovered.resume(resume, "owner-a", response, message),
              Code::FailedPrecondition);
  }
  std::filesystem::remove_all(root);
}

TEST(BatchRegistry, RetryValidatesFailedGroupBeforePublishingMutation) {
  const auto root = fresh_directory();
  const auto input = discover_one(root);
  auto resources = std::make_shared<ResourceManager>(ResourceManagerSettings{});
  CursorSettings settings;
  settings.workers = 1;
  settings.max_memory_bytes = 128 * 1024 * 1024;
  settings.resources = resources;
  ScriptController scripts(settings);
  BatchRegistry registry(scripts, resources, root);

  ctk::analysis::v1::StartBatchRequest request;
  request.set_request_id("retry-request");
  *request.add_inputs() = input;
  const auto blocked_export = root / "output.json";
  std::filesystem::create_directory(blocked_export);
  request.set_body_source("let value = $part.index; save $value to \"" +
                          blocked_export.string() + "\" as json; emit $value;");
  request.set_group_variable("part");
  request.set_size(1);
  request.set_jobs(1);
  ctk::analysis::v1::BatchRun started;
  std::string message;
  auto malformed = request;
  malformed.set_request_id("malformed-request");
  malformed.set_body_source("emit ;");
  ctk::analysis::v1::BatchRun rejected;
  EXPECT_EQ(registry.start(malformed, "retry-owner", rejected, message),
            Code::InvalidArgument);
  EXPECT_TRUE(rejected.run_id().empty());
  ASSERT_EQ(registry.start(request, "retry-owner", started, message), Code::Ok)
      << message;

  const auto failed =
      wait_for_completion(registry, started.run_id(), "retry-owner");
  ASSERT_EQ(failed.state(), "failed") << failed.DebugString();
  ASSERT_EQ(failed.groups_size(), 1);
  EXPECT_EQ(failed.groups(0).state(), "failed");
  EXPECT_TRUE(failed.groups(0).cleanup_acknowledged());
  std::ofstream(root / "fixture.cpp") << "int f() { return 9; }\n";

  ctk::analysis::v1::BatchControlRequest retry;
  retry.set_run_id(started.run_id());
  retry.set_expected_revision(failed.revision());
  ctk::analysis::v1::BatchRun retry_response;
  EXPECT_EQ(registry.retry(retry, "retry-owner", retry_response, message),
            Code::FailedPrecondition);
  ctk::analysis::v1::BatchRunRequest lookup;
  lookup.set_run_id(started.run_id());
  ctk::analysis::v1::BatchRun after_rejection;
  ASSERT_EQ(registry.status(lookup, "retry-owner", after_rejection, message),
            Code::Ok);
  EXPECT_EQ(after_rejection.SerializeAsString(), failed.SerializeAsString());
  std::filesystem::remove_all(root);
}

TEST(BatchRegistry, RetryRechecksCapacityAfterOutOfLockValidation) {
  const auto root = fresh_directory();
  const auto input = discover_one(root);
  auto resources = std::make_shared<ResourceManager>(ResourceManagerSettings{});
  CursorSettings settings;
  settings.workers = 1;
  settings.max_memory_bytes = 128 * 1024 * 1024;
  settings.resources = resources;
  auto engine = std::make_shared<BlockingQueryEngine>();
  ScriptController scripts(settings, engine);
  BatchRegistryLimits limits;
  limits.max_active_runs = 1;
  BatchRegistry registry(scripts, resources, root, limits);

  ctk::analysis::v1::StartBatchRequest first_request;
  first_request.set_request_id("capacity-a");
  *first_request.add_inputs() = input;
  first_request.set_body_source("emit cfg(\"f\", max_blocks=0);");
  first_request.set_group_variable("part");
  first_request.set_size(1);
  first_request.set_jobs(1);
  ctk::analysis::v1::BatchRun first;
  std::string message;
  ASSERT_EQ(registry.start(first_request, "capacity-owner", first, message),
            Code::Ok)
      << message;
  const auto failed =
      wait_for_completion(registry, first.run_id(), "capacity-owner");
  ASSERT_EQ(failed.state(), "failed") << failed.DebugString();

  engine->arm();
  ctk::analysis::v1::BatchControlRequest retry;
  retry.set_run_id(first.run_id());
  retry.set_expected_revision(failed.revision());
  Code retry_code = Code::Ok;
  ctk::analysis::v1::BatchRun retry_response;
  std::string retry_message;
  std::thread retry_thread([&] {
    retry_code =
        registry.retry(retry, "capacity-owner", retry_response, retry_message);
  });
  const bool retry_paused = engine->wait_for_acquisitions(1);
  if (!retry_paused) {
    engine->release();
    retry_thread.join();
    FAIL() << "retry validation did not reach its snapshot barrier";
  }

  auto second_request = first_request;
  second_request.set_request_id("capacity-b");
  second_request.set_body_source("emit $part.index;");
  ctk::analysis::v1::BatchRun second;
  const auto second_start =
      registry.start(second_request, "capacity-owner", second, message);
  if (second_start != Code::Ok) {
    engine->release();
    retry_thread.join();
    FAIL() << message;
  }
  const bool second_paused = engine->wait_for_acquisitions(2);
  engine->release();
  retry_thread.join();
  ASSERT_TRUE(second_paused) << "second run did not reach its snapshot barrier";

  EXPECT_EQ(retry_code, Code::ResourceExhausted) << retry_message;
  ctk::analysis::v1::BatchRunRequest lookup_first;
  lookup_first.set_run_id(first.run_id());
  ctk::analysis::v1::BatchRun unchanged;
  ASSERT_EQ(registry.status(lookup_first, "capacity-owner", unchanged, message),
            Code::Ok)
      << message;
  EXPECT_EQ(unchanged.SerializeAsString(), failed.SerializeAsString());
  const auto second_done =
      wait_for_completion(registry, second.run_id(), "capacity-owner");
  EXPECT_EQ(second_done.state(), "completed") << second_done.DebugString();
  std::filesystem::remove_all(root);
}

TEST(BatchRegistry, ManifestLimitRejectionDoesNotPoisonLaterRuns) {
  const auto root = fresh_directory();
  const auto input = discover_one(root);
  auto resources = std::make_shared<ResourceManager>(ResourceManagerSettings{});
  CursorSettings settings;
  settings.workers = 1;
  settings.max_memory_bytes = 128 * 1024 * 1024;
  settings.resources = resources;
  ScriptController scripts(settings);
  BatchRegistryLimits limits;
  limits.max_manifest_bytes = 4096;
  BatchRegistry registry(scripts, resources, root, limits);

  ctk::analysis::v1::StartBatchRequest oversized;
  oversized.set_request_id("limit-request");
  *oversized.add_inputs() = input;
  oversized.set_body_source(std::string(5000, ' ') + "emit 1;");
  oversized.set_group_variable("part");
  oversized.set_size(1);
  oversized.set_jobs(1);
  ctk::analysis::v1::BatchRun response;
  std::string message;
  EXPECT_EQ(registry.start(oversized, "limit-owner", response, message),
            Code::ResourceExhausted);
  EXPECT_TRUE(response.run_id().empty());

  auto valid = oversized;
  valid.set_body_source("emit $part.index;");
  ASSERT_EQ(registry.start(valid, "limit-owner", response, message), Code::Ok)
      << message;
  ctk::analysis::v1::BatchRunRequest lookup;
  lookup.set_run_id(response.run_id());
  const auto stored =
      wait_for_completion(registry, response.run_id(), "limit-owner");
  EXPECT_EQ(stored.state(), "completed") << stored.DebugString();
  ctk::analysis::v1::BatchRun current;
  EXPECT_EQ(registry.status(lookup, "limit-owner", current, message), Code::Ok)
      << message;
  EXPECT_EQ(current.run_id(), response.run_id());
  std::filesystem::remove_all(root);
}

TEST(BatchRegistry, PostRenameJournalFailureFailsClosedUntilRestart) {
  const auto root = fresh_directory();
  const auto input = discover_one(root);
  auto resources = std::make_shared<ResourceManager>(ResourceManagerSettings{});
  CursorSettings settings;
  settings.workers = 1;
  settings.max_memory_bytes = 128 * 1024 * 1024;
  settings.resources = resources;
  ScriptController scripts(settings);

  auto injected = std::make_shared<std::atomic_bool>(false);
  BatchRegistryLimits limits;
  limits.max_active_runs = 1;
  limits.journal_write = [injected](const std::filesystem::path &path,
                                    std::string_view bytes) {
    ctk::platform::durable_atomic_write(path, bytes);
    ctk::analysis::v1::BatchRun manifest;
    if (!manifest.ParseFromArray(bytes.data(), static_cast<int>(bytes.size())))
      return;
    if (!injected->load() && manifest.groups_size() > 0 &&
        !manifest.groups(0).resource_scope_id().empty() &&
        manifest.groups(0).source_revisions_size() > 0 &&
        manifest.groups(0).source_revisions(0).starts_with("closure:") &&
        !injected->exchange(true))
      throw std::runtime_error("injected post-rename journal failure");
  };
  ctk::analysis::v1::StartBatchRequest request;
  request.set_request_id("post-rename-request");
  *request.add_inputs() = input;
  *request.add_inputs() = input;
  request.set_body_source("emit $part.index;");
  request.set_group_variable("part");
  request.set_size(1);
  request.set_jobs(1);
  request.set_continue_on_error(true);

  std::string run_id;
  {
    BatchRegistry registry(scripts, resources, root, limits);
    ctk::analysis::v1::BatchRun started;
    std::string message;
    ASSERT_EQ(registry.start(request, "journal-owner", started, message),
              Code::Ok)
        << message;
    run_id = started.run_id();

    ctk::analysis::v1::BatchRunRequest lookup;
    lookup.set_run_id(run_id);
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(5);
    Code status = Code::Ok;
    do {
      ctk::analysis::v1::BatchRun response;
      status = registry.status(lookup, "journal-owner", response, message);
      if (status == Code::Internal)
        break;
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
    } while (std::chrono::steady_clock::now() < deadline);
    ASSERT_EQ(status, Code::Internal) << message;
    EXPECT_NE(message.find("fail-closed"), std::string::npos);

    ctk::analysis::v1::BatchRun duplicate;
    EXPECT_EQ(registry.start(request, "journal-owner", duplicate, message),
              Code::Internal);
    auto new_request = request;
    new_request.set_request_id("blocked-new-request");
    EXPECT_EQ(registry.start(new_request, "journal-owner", duplicate, message),
              Code::Internal);
    ctk::analysis::v1::BatchControlRequest cancel;
    cancel.set_run_id(run_id);
    cancel.set_expected_revision(started.revision());
    EXPECT_EQ(registry.cancel(cancel, "journal-owner", duplicate, message),
              Code::Internal);
  }

  std::size_t manifests = 0;
  for (const auto &entry :
       std::filesystem::recursive_directory_iterator(root / "batches")) {
    if (entry.is_regular_file() && entry.path().extension() == ".pb")
      ++manifests;
  }
  ASSERT_EQ(manifests, 1);

  {
    BatchRegistry recovered(scripts, resources, root);
    ctk::analysis::v1::BatchRunRequest lookup;
    lookup.set_run_id(run_id);
    ctk::analysis::v1::BatchRun response;
    std::string message;
    ASSERT_EQ(recovered.status(lookup, "journal-owner", response, message),
              Code::Ok)
        << message;
    EXPECT_EQ(response.state(), "interrupted");
    ASSERT_EQ(response.groups_size(), 2);
    EXPECT_EQ(response.groups(0).state(), "cancelled");
    EXPECT_TRUE(response.groups(0).cleanup_acknowledged());
    EXPECT_FALSE(response.groups(0).resource_scope_id().empty());
    EXPECT_EQ(response.groups(1).state(), "pending");
    ctk::analysis::v1::BatchRun duplicate;
    ASSERT_EQ(recovered.start(request, "journal-owner", duplicate, message),
              Code::Ok)
        << message;
    EXPECT_EQ(duplicate.run_id(), run_id);
  }
  std::filesystem::remove_all(root);
}
#endif

} // namespace ctk::application
