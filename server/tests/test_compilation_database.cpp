#include "ctk/clang/compilation_database.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <gtest/gtest.h>

namespace ctk::clang_layer {
namespace {
void write_database(const std::filesystem::path &database,
                    const std::filesystem::path &directory,
                    const std::string &file,
                    const std::vector<std::string> &arguments,
                    bool shell_command = false) {
  google::protobuf::ListValue entries;
  auto *entry = entries.add_values()->mutable_struct_value();
  auto &fields = *entry->mutable_fields();
  fields["directory"].set_string_value(directory.string());
  fields["file"].set_string_value(file);
  if (shell_command) {
    std::string command;
    for (const auto &argument : arguments)
      command += "'" + argument + "' ";
    fields["command"].set_string_value(command);
  } else {
    auto *list = fields["arguments"].mutable_list_value();
    for (const auto &argument : arguments)
      list->add_values()->set_string_value(argument);
  }
  std::string json;
  ASSERT_TRUE(google::protobuf::util::MessageToJsonString(entries, &json).ok());
  std::ofstream(database) << json;
}

int match_count(const std::shared_ptr<IQueryEngine> &engine,
                const FileInput &file, const std::string &name) {
  int count = 0;
  const auto result = engine->match(
      file, "functionDecl(hasName(\"" + name + "\")).bind(\"f\")",
      [] { return true; }, [&](const auto &) { ++count; });
  EXPECT_TRUE(result.ok) << result.message;
  return count;
}
} // namespace

TEST(CompilationDatabase,
     AutomaticallyUsesBuildDatabaseAndCommandWorkingDirectory) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-auto"};
  std::filesystem::create_directories(project.path() /
                                      "build/include with spaces");
  std::filesystem::create_directory(project.path() / "src");
  std::ofstream(project.path() / "build/include with spaces/profile.hpp")
      << "#define PROFILE_VALUE 17\n";
  std::ofstream(project.path() / "src/file.cc")
      << "#include <profile.hpp>\nstatic_assert(PROFILE_VALUE == 17);\nint "
         "from_database(){return PROFILE_VALUE;}";
  write_database(project.path() / "build/compile_commands.json",
                 project.path() / "build", "../src/file.cc",
                 {"clang++", "-std=c++20", "-Iinclude with spaces", "-c",
                  "../src/file.cc", "-o", "file.o", "-MMD", "-MF", "file.d"},
                 true);
  FileInput input{"src/file.cc", {}, project.path().string()};
  const auto resolved = resolve_compilation_command(input);
  EXPECT_EQ(
      resolved.working_directory,
      std::filesystem::weakly_canonical(project.path() / "build").string());
  EXPECT_EQ(match_count(make_query_engine(), input, "from_database"), 1);
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/file.o"));
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/file.d"));
}

TEST(CompilationDatabase,
     ExplicitPathOverridesDiscoveryAndRequestFlagsOverrideDatabase) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-explicit"};
  std::ofstream(project.path() / "file.cc")
      << "static_assert(VALUE == 23); int selected(){return VALUE;}";
  write_database(project.path() / "compile_commands.json", project.path(),
                 "file.cc", {"clang++", "-DVALUE=1", "file.cc"});
  write_database(project.path() / "alternative.json", project.path(), "file.cc",
                 {"clang++", "-DVALUE=2", "file.cc"});
  FileInput input{"file.cc",
                  {"-UVALUE", "-DVALUE=23"},
                  project.path().string(),
                  "alternative.json"};
  EXPECT_EQ(match_count(make_query_engine(), input, "selected"), 1);
}

TEST(CompilationDatabase, ChangedDatabaseSelectsNewAstRatherThanStaleFlags) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-refresh"};
  std::ofstream(project.path() / "file.cc")
      << "#if VALUE == 1\nint before(){return 1;}\n#else\nint after(){return "
         "2;}\n#endif\n";
  auto database = project.path() / "compile_commands.json";
  write_database(database, project.path(), "file.cc",
                 {"clang++", "-DVALUE=1", "file.cc"});
  FileInput input{"file.cc", {}, project.path().string()};
  auto engine = make_query_engine();
  EXPECT_EQ(match_count(engine, input, "before"), 1);
  EXPECT_EQ(match_count(engine, input, "before"), 1);
  write_database(database, project.path(), "file.cc",
                 {"clang++", "-DVALUE=22", "file.cc"});
  EXPECT_EQ(match_count(engine, input, "after"), 1);
  EXPECT_EQ(match_count(engine, input, "before"), 0);
  std::ofstream(database) << "[invalid JSON";
  EXPECT_THROW(resolve_compilation_command(input), std::invalid_argument);
}

TEST(CompilationDatabase,
     ExpandsResponseFilesInCommandDirectoryAndRefreshesTheirFlags) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-response"};
  std::filesystem::create_directory(project.path() / "build");
  std::ofstream(project.path() / "file.cc")
      << "#if VALUE == 1\nint before(){return 1;}\n#else\nint after(){return "
         "2;}\n#endif\n";
  auto response = project.path() / "build/flags.rsp";
  std::ofstream(response)
      << "-DVALUE=1 -c ../file.cc -o output.o -MMD -MF output.d";
  write_database(project.path() / "build/compile_commands.json",
                 project.path() / "build", "../file.cc",
                 {"clang++", "@flags.rsp"});
  FileInput input{"file.cc", {}, project.path().string()};
  auto engine = make_query_engine();
  EXPECT_EQ(match_count(engine, input, "before"), 1);
  std::ofstream(response) << "-DVALUE=22 -c ../file.cc -o output.o";
  EXPECT_EQ(match_count(engine, input, "after"), 1);
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/output.o"));
  EXPECT_FALSE(std::filesystem::exists(project.path() / "build/output.d"));
}

TEST(CompilationDatabase, ExplicitMissingFilesAndCommandsAreErrors) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-missing"};
  std::ofstream(project.path() / "file.cc") << "int value;";
  FileInput input{"file.cc", {}, project.path().string(), "absent.json"};
  EXPECT_THROW(resolve_compilation_command(input), std::invalid_argument);
  write_database(project.path() / "compile_commands.json", project.path(),
                 "other.cc", {"clang++", "other.cc"});
  input.compilation_database = project.path().string();
  EXPECT_THROW(resolve_compilation_command(input), std::invalid_argument);
  input.compilation_database.clear();
  EXPECT_EQ(resolve_compilation_command(input).path, input.path);
}

TEST(CompilationDatabase, ParseFailureReportsMissingHeaderAndSourceLocation) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-diagnostics"};
  std::ofstream(project.path() / "file.cc")
      << "#include <ctk_missing_project_header.hpp>\nint value;\n";
  write_database(project.path() / "compile_commands.json", project.path(),
                 "file.cc", {"clang++", "-std=c++20", "file.cc"});
  FileInput input{"file.cc", {}, project.path().string()};
  auto engine = make_query_engine();
  try {
    engine->acquire_snapshot(input);
    FAIL() << "missing header must fail parsing";
  } catch (const std::exception &error) {
    const std::string message = error.what();
    EXPECT_NE(message.find("file.cc:1:10:"), std::string::npos) << message;
    EXPECT_NE(message.find("ctk_missing_project_header.hpp"), std::string::npos)
        << message;
    EXPECT_NE(message.find("file not found"), std::string::npos) << message;
  }
  // Failed snapshots must remain retryable after the build inputs are fixed.
  std::ofstream(project.path() / "file.cc") << "int recovered(){return 1;}";
  EXPECT_EQ(match_count(engine, input, "recovered"), 1);
}

TEST(CompilationDatabase, ParseFailureReportsDriverAndPreprocessorErrors) {
  ctk::platform::TemporaryDirectory project{"ctk-compdb-driver-diagnostics"};
  std::ofstream(project.path() / "file.cc")
      << "#error project_profile_missing\n";
  FileInput input{"file.cc", {}, project.path().string()};
  auto engine = make_query_engine();
  auto result = engine->match(
      input, "varDecl().bind(\"v\")", [] { return true; }, [](const auto &) {});
  EXPECT_FALSE(result.ok);
  EXPECT_NE(result.message.find("project_profile_missing"), std::string::npos)
      << result.message;
  input.compile_arguments = {"-ctk-invalid-driver-option"};
  result = engine->match(
      input, "varDecl().bind(\"v\")", [] { return true; }, [](const auto &) {});
  EXPECT_FALSE(result.ok);
  EXPECT_NE(result.message.find("-ctk-invalid-driver-option"),
            std::string::npos)
      << result.message;
  input.compile_arguments = {"-include"};
  result = engine->match(
      input, "varDecl().bind(\"v\")", [] { return true; }, [](const auto &) {});
  EXPECT_FALSE(result.ok);
  EXPECT_FALSE(result.message.empty());
}
} // namespace ctk::clang_layer
