#include <ctk/net/index_service.hpp>

#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <filesystem>
#include <fstream>

namespace {
namespace fs = std::filesystem;
namespace pb = ctk::index::v1;

class ProjectIndexNames : public testing::Test {
protected:
  fs::path directory;

  void SetUp() override {
    static std::atomic<unsigned> sequence{0};
    directory =
        fs::temp_directory_path() /
        ("ctk-project-names-" +
         std::to_string(
             std::chrono::steady_clock::now().time_since_epoch().count()) +
         "-" + std::to_string(sequence++));
    fs::create_directories(directory / "project");
    std::ofstream(directory / "project" / "compile_commands.json") << "[]";
  }
  void TearDown() override {
    std::error_code error;
    fs::remove_all(directory, error);
  }
  pb::StartProjectIndexRequest start_request() const {
    pb::StartProjectIndexRequest request;
    request.set_project_root((directory / "project").string());
    return request;
  }
};

TEST_F(ProjectIndexNames,
       NamesPersistForLiveAndIdleIndexesWithoutRestartingWork) {
  std::string root;
  {
    ctk::net::IndexServiceAdapter service(directory / "storage",
                                          [] { return true; });
    grpc::ServerContext context;
    auto request = start_request();
    request.set_project_name("My library");
    pb::ProjectIndexStatus started;
    ASSERT_TRUE(service.StartProjectIndex(&context, &request, &started).ok());
    EXPECT_EQ(started.project_name(), "My library");
    root = started.project_root();
    pb::ProjectIndexRequest project;
    project.set_project_root(root);
    pb::ProjectIndexStatus paused;
    ASSERT_TRUE(service.PauseProjectIndex(&context, &project, &paused).ok());
    pb::RenameProjectIndexRequest rename;
    rename.set_project_root(root);
    rename.set_project_name("Renamed library");
    pb::ProjectIndexStatus renamed;
    ASSERT_TRUE(service.RenameProjectIndex(&context, &rename, &renamed).ok());
    EXPECT_EQ(renamed.project_root(), root);
    EXPECT_EQ(renamed.project_name(), "Renamed library");
    EXPECT_EQ(renamed.state(), pb::INDEX_STATE_PAUSED) << renamed.error();
    EXPECT_EQ(renamed.revision(), paused.revision());
    EXPECT_EQ(renamed.translation_units_indexed(),
              paused.translation_units_indexed());
    // Starting an already running monitor without a name preserves its name.
    request.clear_project_name();
    ASSERT_TRUE(service.StartProjectIndex(&context, &request, &started).ok());
    EXPECT_EQ(started.project_name(), "Renamed library");
    EXPECT_EQ(started.state(), pb::INDEX_STATE_PAUSED) << started.error();
  }
  {
    ctk::net::IndexServiceAdapter service(directory / "storage",
                                          [] { return true; });
    grpc::ServerContext context;
    pb::ListProjectIndexesRequest list;
    pb::ListProjectIndexesResponse saved;
    ASSERT_TRUE(service.ListProjectIndexes(&context, &list, &saved).ok());
    ASSERT_EQ(saved.projects_size(), 1);
    EXPECT_EQ(saved.projects(0).project_name(), "Renamed library");
    EXPECT_EQ(saved.projects(0).state(), pb::INDEX_STATE_IDLE);
    pb::RenameProjectIndexRequest rename;
    rename.set_project_root(root);
    rename.set_project_name("Final library");
    pb::ProjectIndexStatus renamed;
    ASSERT_TRUE(service.RenameProjectIndex(&context, &rename, &renamed).ok());
    EXPECT_EQ(renamed.project_name(), "Final library");
    EXPECT_EQ(renamed.state(), pb::INDEX_STATE_IDLE);
    auto request = start_request();
    pb::ProjectIndexStatus started;
    ASSERT_TRUE(service.StartProjectIndex(&context, &request, &started).ok());
    EXPECT_EQ(started.project_name(), "Final library");
  }
}

TEST_F(ProjectIndexNames, DefaultsAndExplicitUpdatesPreserveProjectIdentity) {
  ctk::net::IndexServiceAdapter service(directory / "storage",
                                        [] { return true; });
  grpc::ServerContext context;
  auto request = start_request();
  pb::ProjectIndexStatus original;
  ASSERT_TRUE(service.StartProjectIndex(&context, &request, &original).ok());
  EXPECT_EQ(original.project_name(), "project");
  request.set_project_name("Custom name");
  pb::ProjectIndexStatus updated;
  ASSERT_TRUE(service.StartProjectIndex(&context, &request, &updated).ok());
  EXPECT_EQ(updated.project_name(), "Custom name");
  EXPECT_EQ(updated.project_root(), original.project_root());
  EXPECT_EQ(updated.revision(), original.revision());
}

TEST_F(ProjectIndexNames, InvalidNamesAndUnknownProjectsDoNotCreateIndexes) {
  ctk::net::IndexServiceAdapter service(directory / "storage",
                                        [] { return true; });
  grpc::ServerContext context;
  for (const auto *name :
       {"", " ", ".", "..", "*", "~home", "a/b", "bad\nname", " padded "}) {
    auto request = start_request();
    request.set_project_name(name);
    pb::ProjectIndexStatus result;
    EXPECT_EQ(
        service.StartProjectIndex(&context, &request, &result).error_code(),
        grpc::StatusCode::INVALID_ARGUMENT);
    pb::RenameProjectIndexRequest rename;
    rename.set_project_root(request.project_root());
    rename.set_project_name(name);
    EXPECT_EQ(
        service.RenameProjectIndex(&context, &rename, &result).error_code(),
        grpc::StatusCode::INVALID_ARGUMENT);
  }
  pb::RenameProjectIndexRequest rename;
  rename.set_project_root(start_request().project_root());
  rename.set_project_name("Valid name");
  pb::ProjectIndexStatus result;
  EXPECT_EQ(service.RenameProjectIndex(&context, &rename, &result).error_code(),
            grpc::StatusCode::FAILED_PRECONDITION);
  pb::ListProjectIndexesRequest list;
  pb::ListProjectIndexesResponse saved;
  ASSERT_TRUE(service.ListProjectIndexes(&context, &list, &saved).ok());
  EXPECT_EQ(saved.total_count(), 0);
}
} // namespace
