#include "ctk/storage/store.hpp"

#include <sqlite3.h>

#include <filesystem>
#include <fstream>
#include <random>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#include <gtest/gtest.h>

namespace {

class TemporaryRoot final {
public:
  TemporaryRoot() {
    auto seed = std::filesystem::temp_directory_path() /
                ("ctk-storage-" + std::to_string(std::random_device{}()));
    path_ = std::move(seed);
  }
  ~TemporaryRoot() {
    std::error_code ignored;
    std::filesystem::remove_all(path_, ignored);
  }
  const std::filesystem::path &path() const { return path_; }

private:
  std::filesystem::path path_;
};

ctk::storage::StoreOptions options(const std::filesystem::path &root) {
  ctk::storage::StoreOptions result;
  result.root = root;
  return result;
}

ctk::storage::SnapshotDraft draft(std::string manifest = "generation-one",
                                  std::string bytes = "native-tu-bytes") {
  using namespace ctk::storage;
  SnapshotDraft result;
  result.profile.main_path = "/work/project/main.cc";
  result.profile.toolchain.clang_version = "22.1.8";
  result.profile.toolchain.build_identity = "clang-test-build";
  result.profile.toolchain.target_triple = "arm64-apple-darwin";
  result.profile.toolchain.resource_directory = "/toolchain/resource";
  result.profile.toolchain.resource_content_identity = "resource-tree-sha256";
  result.profile.input_spelling = "main.cc";
  result.profile.working_directory = "/work/project";
  result.profile.arguments = {"-std=c++23"};
  const auto generation_digest = manifest == "generation-one"
      ? std::string(64, 'a') : std::string(64, 'c');
  result.inputs.push_back({"/work/project/main.cc", InputRole::MainSource,
                           ObservationKind::Content,
                           generation_digest, 12, 100, "main-buffer"});
  result.inputs.push_back({"/work/project/include/new.h", InputRole::Lookup,
                           ObservationKind::Absent, {}, {}, {}, "include-search-0"});
  result.inputs.push_back({"/work/project/include/", InputRole::Lookup,
                           ObservationKind::Directory, std::string(64, 'b'),
                           {}, 101, "namespace-v1"});
  result.artifacts.push_back({ArtifactKind::TranslationUnit,
                              "/work/project/main.cc", std::move(bytes)});
  return result;
}

std::int64_t scalar(sqlite3 *database, const char *sql) {
  sqlite3_stmt *statement = nullptr;
  if (sqlite3_prepare_v2(database, sql, -1, &statement, nullptr) != SQLITE_OK)
    throw std::runtime_error(sqlite3_errmsg(database));
  const int status = sqlite3_step(statement);
  if (status != SQLITE_ROW) {
    sqlite3_finalize(statement);
    throw std::runtime_error(sqlite3_errmsg(database));
  }
  const auto value = sqlite3_column_int64(statement, 0);
  sqlite3_finalize(statement);
  return value;
}

void execute(sqlite3 *database, const char *sql) {
  char *error = nullptr;
  const auto status = sqlite3_exec(database, sql, nullptr, nullptr, &error);
  if (status == SQLITE_OK) return;
  const std::string message = error ? error : sqlite3_errmsg(database);
  sqlite3_free(error);
  throw std::runtime_error(message);
}

std::filesystem::path find_blob(const std::filesystem::path &root) {
  for (const auto &entry : std::filesystem::recursive_directory_iterator(root / "blobs"))
    if (entry.is_regular_file() && entry.path().extension() == ".ast")
      return entry.path();
  throw std::runtime_error("test blob not found");
}

TEST(StorageStore, PublishesAndReadsNativeBlobWithExactV1Schema) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto store = Store::open(options(root.path()));
  const auto id = store->publish(draft());
  auto leases = store->acquire_ready(draft().profile);
  ASSERT_EQ(leases.size(), 1U);
  EXPECT_EQ(leases.front()->descriptor().id, id);
  EXPECT_EQ(leases.front()->read_artifact(0), "native-tu-bytes");
  ASSERT_EQ(leases.front()->descriptor().inputs.size(), 3U);
  EXPECT_EQ(leases.front()->descriptor().inputs[0].role, InputRole::MainSource);
  EXPECT_EQ(leases.front()->descriptor().inputs[1].kind, ObservationKind::Absent);
  EXPECT_EQ(leases.front()->descriptor().inputs[2].kind, ObservationKind::Directory);

  sqlite3 *database = nullptr;
  ASSERT_EQ(sqlite3_open((root.path() / "index.sqlite3").c_str(), &database), SQLITE_OK);
  EXPECT_EQ(scalar(database,
      "SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"), 9);
  EXPECT_EQ(scalar(database,
      "SELECT sum((SELECT count(*) FROM pragma_table_info(m.name))) FROM sqlite_master m WHERE type='table' AND name NOT LIKE 'sqlite_%'"), 48);
  EXPECT_EQ(scalar(database,
      "SELECT count(*) FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"), 8);
  EXPECT_EQ(scalar(database,
      "SELECT count(*) FROM sqlite_master WHERE type='trigger'"), 3);
  EXPECT_EQ(scalar(database, "PRAGMA user_version"), 1);
  sqlite3_close(database);
}

TEST(StorageStore, PruneUnusedPreservesLeasesAndCollectsAfterRelease) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto store = Store::open(options(root.path()));
  store->publish(draft());
  auto lease = store->acquire_ready(draft().profile).front();
  auto unused = draft("second-artifact");
  unused.profile.arguments.emplace_back("-DOTHER_PROFILE=1");
  store->publish(unused);
  store->prune_unused();
  EXPECT_EQ(store->stats().ready_snapshots, 1U);
  EXPECT_EQ(lease->read_artifact(0), "native-tu-bytes");
  lease.reset();
  store->prune_unused();
  EXPECT_EQ(store->stats().ready_snapshots, 0U);
  EXPECT_EQ(store->stats().physical_bytes, 0U);
}

TEST(StorageStore, RetirementBlocksNewLeasesAndWaitsForExistingLease) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto store = Store::open(options(root.path()));
  const auto id = store->publish(draft());
  auto lease = store->acquire_ready(draft().profile).front();
  store->retire(id);
  EXPECT_TRUE(store->acquire_ready(draft().profile).empty());
  EXPECT_EQ(lease->read_artifact(0), "native-tu-bytes");
  lease.reset();
  EXPECT_EQ(store->stats().leased_snapshots, 0U);
  EXPECT_EQ(store->stats().ready_snapshots, 0U);
  EXPECT_EQ(store->stats().physical_bytes, 0U);
}

TEST(StorageStore, SharedBlobSurvivesRetirementOfOneSnapshot) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto store = Store::open(options(root.path()));
  const auto first = store->publish(draft("one"));
  const auto second = store->publish(draft("two"));
  auto leases = store->acquire_ready(draft().profile);
  ASSERT_EQ(leases.size(), 2U);
  store->retire(first);
  EXPECT_EQ(leases[1]->read_artifact(0), "native-tu-bytes");
  leases.clear();
  auto remaining = store->acquire_ready(draft().profile);
  ASSERT_EQ(remaining.size(), 1U);
  EXPECT_EQ(remaining.front()->descriptor().id, second);
}

TEST(StorageStore, RejectsInvalidClosureWithoutPublishing) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto store = Store::open(options(root.path()));
  auto invalid = draft();
  invalid.artifacts.push_back({ArtifactKind::Module, "/work/project/module.pcm", "module"});
  EXPECT_THROW(store->publish(invalid), std::invalid_argument);
  EXPECT_EQ(store->stats().ready_snapshots, 0U);
  EXPECT_EQ(store->stats().physical_bytes, 0U);
}

TEST(StorageStore, ValidatesReachableAcyclicArtifactClosure) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto store = Store::open(options(root.path()));
  auto valid = draft();
  valid.artifacts.push_back({ArtifactKind::Pch, "/work/project/pch.pch", "pch"});
  valid.artifacts.push_back({ArtifactKind::Module, "/work/project/module.pcm", "module"});
  valid.dependencies = {{0, 1}, {1, 2}};
  EXPECT_NO_THROW(store->publish(valid));

  auto cyclic = draft("cycle");
  cyclic.artifacts.insert(cyclic.artifacts.end(),
      {{ArtifactKind::Pch, "/work/project/pch2.pch", "pch"},
       {ArtifactKind::Module, "/work/project/module2.pcm", "module"}});
  cyclic.dependencies = {{0, 1}, {1, 2}, {2, 0}};
  EXPECT_THROW(store->publish(cyclic), std::invalid_argument);

  auto unreachable = draft("unreachable");
  unreachable.artifacts.push_back(
      {ArtifactKind::Module, "/work/project/orphan.pcm", "orphan"});
  EXPECT_THROW(store->publish(unreachable), std::invalid_argument);
}

TEST(StorageStore, KeepsCompilationProfilesAndToolchainsSeparate) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto store = Store::open(options(root.path()));
  auto first = draft("first");
  auto second = draft("second");
  second.profile.arguments.push_back("-DSECOND");
  second.profile.toolchain.build_identity = "clang-other";
  EXPECT_NE(store->publish(first), store->publish(second));
  EXPECT_EQ(store->acquire_ready(first.profile).size(), 1U);
  EXPECT_EQ(store->acquire_ready(second.profile).size(), 1U);
}

TEST(StorageStore, FullCanonicalBytesDefeatAStoredDigestHit) {
  using namespace ctk::storage;
  TemporaryRoot root;
  const auto path = root.path() / "index.sqlite3";
  auto store = Store::open(options(root.path()));
  store->publish(draft());
  store.reset();

  sqlite3 *database = nullptr;
  ASSERT_EQ(sqlite3_open(path.c_str(), &database), SQLITE_OK);
  execute(database,
      "UPDATE compilation_profiles SET canonical_context='ctk-profile-v1:{\"changed\":true}'");
  sqlite3_close(database);

  store = Store::open(options(root.path()));
  EXPECT_TRUE(store->acquire_ready(draft().profile).empty());
}

TEST(StorageStore, RecoveryMarksMissingAndCorruptBlobsStale) {
  using namespace ctk::storage;
  for (const bool corrupt : {false, true}) {
    TemporaryRoot root;
    {
      auto store = Store::open(options(root.path()));
      store->publish(draft());
    }
    const auto blob = find_blob(root.path());
    if (corrupt) {
      std::ofstream output(blob, std::ios::binary | std::ios::trunc);
      output << "corrupt";
    } else {
      std::filesystem::remove(blob);
    }
    auto recovered = Store::open(options(root.path()));
    EXPECT_EQ(recovered->stats().stale_snapshots, 1U);
    EXPECT_TRUE(recovered->acquire_ready(draft().profile).empty());
  }
}

TEST(StorageStore, PinnedClosureDefersQuotaCollectionAndFailedWriteCleansUp) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto limited = options(root.path());
  limited.max_physical_bytes = 24;
  auto store = Store::open(limited);
  const auto id = store->publish(draft());
  auto lease = store->acquire_ready(draft().profile).front();
  auto larger = draft("larger", "native-tu-bytes-that-are-longer");
  EXPECT_THROW(store->publish(larger), std::runtime_error);
  EXPECT_EQ(store->acquire_ready(draft().profile).size(), 1U);
  EXPECT_EQ(lease->descriptor().id, id);
  EXPECT_EQ(lease->read_artifact(0), "native-tu-bytes");
  lease.reset();
  EXPECT_EQ(store->stats().physical_bytes, std::string("native-tu-bytes").size());
}

TEST(StorageStore, UnsupportedCanonicalVersionsBypassPublication) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto store = Store::open(options(root.path()));
  auto unsupported = draft();
  unsupported.profile.schema_version = 99;
  EXPECT_THROW(store->publish(unsupported), std::invalid_argument);
  EXPECT_EQ(store->stats().ready_snapshots, 0U);
}

TEST(StorageStore, RejectsNonReusableProfiles) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto store = Store::open(options(root.path()));
  store->publish(draft());
  auto non_reusable = draft();
  non_reusable.profile.reusable = false;
  EXPECT_THROW(store->publish(non_reusable), std::invalid_argument);
  EXPECT_TRUE(store->acquire_ready(non_reusable.profile).empty());
}

TEST(StorageStore, RecoveryWaitsForConcurrentPublication) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto store = Store::open(options(root.path()));
  std::thread publisher([&] {
    for (int index = 0; index < 20; ++index)
      store->publish(draft("generation-one", "native-tu-bytes"));
  });
  std::thread recovery([&] {
    for (int index = 0; index < 20; ++index) store->recover();
  });
  publisher.join();
  recovery.join();
  const auto leases = store->acquire_ready(draft().profile);
  ASSERT_FALSE(leases.empty());
  for (const auto &lease : leases)
    EXPECT_EQ(lease->read_artifact(0), "native-tu-bytes");
}

TEST(StorageStore, RejectsNewerSchemaBeforeChangingIt) {
  using namespace ctk::storage;
  TemporaryRoot root;
  std::filesystem::create_directories(root.path());
  sqlite3 *database = nullptr;
  const auto path = root.path() / "index.sqlite3";
  ASSERT_EQ(sqlite3_open(path.c_str(), &database), SQLITE_OK);
  ASSERT_EQ(sqlite3_exec(database,
      "CREATE TABLE sentinel(value TEXT); PRAGMA user_version=73",
      nullptr, nullptr, nullptr), SQLITE_OK);
  sqlite3_close(database);

  EXPECT_THROW(Store::open(options(root.path())), std::runtime_error);
  ASSERT_EQ(sqlite3_open(path.c_str(), &database), SQLITE_OK);
  EXPECT_EQ(scalar(database, "PRAGMA user_version"), 73);
  EXPECT_EQ(scalar(database,
      "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='sentinel'"), 1);
  sqlite3_close(database);
}

TEST(StorageStore, EnforcesExclusiveCacheRootOwnership) {
  using namespace ctk::storage;
  TemporaryRoot root;
  auto first = Store::open(options(root.path()));
  EXPECT_THROW(Store::open(options(root.path())), std::system_error);
}

} // namespace
