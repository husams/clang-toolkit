#include "ctk/clang/file_discovery.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <gtest/gtest.h>

namespace ctk::clang_layer {
namespace {
ctk::match::v1::InputDescriptor input(const std::filesystem::path &root,
                                      const std::string &name) {
  ctk::match::v1::InputDescriptor result;
  result.set_file_path(name);
  result.mutable_profile()->set_working_directory(root.string());
  return result;
}
} // namespace

TEST(FileDiscovery, StableManifestContainsMetadataWithoutNativeAcquisition) {
  ctk::platform::TemporaryDirectory fixture{"ctk-discovery"};
  std::filesystem::create_directory(fixture.path() / "nested");
  std::ofstream(fixture.path() / "z.cc") << "void z(){}";
  std::ofstream(fixture.path() / "nested/a.cc") << "void a(){}";
  std::ofstream(fixture.path() / "included.hpp") << "void header();";
  ctk::match::v1::DiscoverFilesRequest request;
  request.add_paths("**/*.cc");
  request.add_paths("z.cc");
  request.mutable_profile()->set_working_directory(fixture.path().string());
  const auto engine = make_query_engine();
  const auto before = engine->resources();
  const auto manifest = discover_file_descriptors(request);
  ASSERT_EQ(manifest.inputs_size(), 2);
  EXPECT_TRUE(manifest.inputs(0).file_path().ends_with("nested/a.cc"));
  EXPECT_TRUE(manifest.inputs(1).file_path().ends_with("z.cc"));
  EXPECT_EQ(manifest.inputs(0).profile().profile_id(),
            manifest.inputs(1).profile().profile_id());
  EXPECT_TRUE(manifest.inputs(0).profile().frozen());
  EXPECT_GT(manifest.inputs(0).source_bytes(), 0);
  EXPECT_EQ(engine->resources().reusable_snapshots(),
            before.reusable_snapshots());
}

TEST(FileDiscovery,
     DifferentProfilesOfOnePathRemainDistinctAndGuardsRejectChanges) {
  ctk::platform::TemporaryDirectory fixture{"ctk-discovery-profiles"};
  std::ofstream(fixture.path() / "file.cc") << "int value;";
  auto first = input(fixture.path(), "file.cc");
  first.mutable_profile()->add_compile_arguments("-DPROFILE=1");
  auto second = first;
  second.mutable_profile()->set_compile_arguments(0, "-DPROFILE=2");
  ctk::match::v1::DiscoverFilesRequest request;
  *request.add_inputs() = first;
  *request.add_inputs() = second;
  *request.add_inputs() = first;
  const auto manifest = discover_file_descriptors(request);
  ASSERT_EQ(manifest.inputs_size(), 2);
  EXPECT_NE(manifest.inputs(0).profile().profile_id(),
            manifest.inputs(1).profile().profile_id());
  auto tampered = manifest.inputs(0);
  tampered.mutable_profile()->add_compile_arguments("-DCHANGED=1");
  EXPECT_THROW(resolve_file_descriptor(tampered), ProfileMismatch);
}

TEST(FileDiscovery, FrozenDatabaseProfileSurvivesDatabaseAndSourceChanges) {
  ctk::platform::TemporaryDirectory fixture{"ctk-discovery-frozen"};
  auto source = fixture.path() / "file.cc";
  std::ofstream(source)
      << "static_assert(PROFILE == 17); int initial(){return PROFILE;}";
  auto database = fixture.path() / "compile_commands.json";
  std::ofstream(database)
      << "[{\"directory\":\"" << fixture.path().string()
      << "\",\"file\":\"file.cc\",\"arguments\":[\"clang++\",\"-DPROFILE=17\","
         "\"-c\",\"file.cc\",\"-o\",\"file.o\"]}]";
  auto selected = input(fixture.path(), "file.cc");
  selected.mutable_profile()->set_compilation_database(database.string());
  const auto frozen = resolve_file_descriptor(selected);
  std::ofstream(database) << "[]";
  std::ofstream(source)
      << "static_assert(PROFILE == 17); int changed(){return PROFILE;}";
  const auto refreshed = resolve_file_descriptor(frozen.descriptor);
  EXPECT_EQ(refreshed.descriptor.profile().profile_id(),
            frozen.descriptor.profile().profile_id());
  auto engine = make_query_engine();
  std::size_t count = 0;
  const auto result = engine->match(
      refreshed.file, "functionDecl(hasName(\"changed\"))", [] { return true; },
      [&](const auto &) { ++count; });
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_EQ(count, 1);
  EXPECT_FALSE(std::filesystem::exists(fixture.path() / "file.o"));
}

TEST(FileDiscovery, BoundsRejectWholeManifestBeforeNativeAcquisition) {
  ctk::platform::TemporaryDirectory fixture{"ctk-discovery-bounds"};
  std::ofstream(fixture.path() / "a.cc") << "int a;";
  std::ofstream(fixture.path() / "b.cc") << "int b;";
  ctk::match::v1::DiscoverFilesRequest request;
  request.add_paths(".");
  request.mutable_profile()->set_working_directory(fixture.path().string());
  request.set_max_inputs(1);
  EXPECT_THROW(discover_file_descriptors(request), std::length_error);
  request.set_max_inputs(10);
  EXPECT_THROW(discover_file_descriptors(request, [] { return false; }),
               std::runtime_error);
  request.set_max_metadata_bytes(1);
  EXPECT_THROW(discover_file_descriptors(request), std::length_error);
}

TEST(FileDiscovery, PreservesSourceAndWorkingDirectorySymlinkSpelling) {
  ctk::platform::TemporaryDirectory fixture{"ctk-discovery-spelling"};
  std::filesystem::create_directory(fixture.path() / "physical");
  std::ofstream(fixture.path() / "physical/a.cc") << "int a;";
  std::filesystem::create_directory_symlink("physical",
                                            fixture.path() / "alias");
  const auto alias = fixture.path() / "alias";
  const auto resolved = resolve_file_descriptor(input(alias, "./a.cc"));
  EXPECT_EQ(resolved.file.path, (alias / "a.cc").string());
  EXPECT_EQ(resolved.file.working_directory, alias.string());
}

TEST(FileDiscovery,
     DatabaseLookupPreservesSourceSymlinkAndRelativePathIdentity) {
  ctk::platform::TemporaryDirectory fixture{"ctk-discovery-database-spelling"};
  const auto physical = fixture.path() / "physical";
  std::filesystem::create_directories(physical / "build");
  std::ofstream(physical / "a.cc")
      << "static_assert(PROFILE == 17); int selected(){return PROFILE;}";
  std::filesystem::create_directory_symlink("physical",
                                            fixture.path() / "alias");
  const auto database = physical / "build/compile_commands.json";
  std::ofstream(database)
      << "[{\"directory\":\"" << (physical / "build").string()
      << "\",\"file\":\"../a.cc\",\"arguments\":[\"clang++\","
         "\"-DPROFILE=17\",\"-c\",\"../a.cc\"]}]";
  const auto alias = fixture.path() / "alias";
  auto selected = input(alias, "./a.cc");
  selected.mutable_profile()->set_compilation_database(database.string());
  const auto resolved = resolve_file_descriptor(selected);
  EXPECT_EQ(resolved.file.path, (alias / "a.cc").string());
  const auto reacquired = resolve_file_descriptor(resolved.descriptor);
  EXPECT_EQ(reacquired.file.path, resolved.file.path);
  EXPECT_EQ(reacquired.descriptor.profile().profile_id(),
            resolved.descriptor.profile().profile_id());
  auto engine = make_query_engine();
  std::size_t count = 0;
  const auto result = engine->match(
      reacquired.file, "functionDecl(hasName(\"selected\"))",
      [] { return true; }, [&](const auto &) { ++count; });
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_EQ(count, 1);
}
} // namespace ctk::clang_layer
