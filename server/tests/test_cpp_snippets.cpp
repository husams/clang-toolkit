#include "ctk/application/match_controller.hpp"
#ifdef CTK_BUILD_SCRIPT
#include "ctk/application/script_controller.hpp"
#endif
#include "ctk/clang/cpp_snippet.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <filesystem>
#include <fstream>
#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <gtest/gtest.h>

namespace ctk::application {
namespace {
using ctk::clang_layer::MatchCode;
using namespace ctk::match::v1;

class CppSnippets : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory directory{"ctk-cpp-snippet-tests"};
  std::unique_ptr<MatchController> controller =
      std::make_unique<MatchController>();

  void database() {
    std::filesystem::create_directories(directory.path() / "src");
    std::filesystem::create_directories(directory.path() / "build/include");
    std::ofstream(directory.path() / "src/z.cpp") << "int z;";
    std::ofstream(directory.path() / "src/a.cpp") << "int a;";
    std::ofstream(directory.path() / "src/template_type.hpp")
        << "#pragma once\nstruct MyTest { int value = 0; };\n"
           "template<class T> struct TemplateType { void add(T item) { "
           "item.value += PROFILE; } };\n";
    std::ofstream(directory.path() / "build/include/relative.hpp")
        << "#pragma once\n#define FROM_RELATIVE_INCLUDE 23\n";
    std::ofstream(directory.path() / "build/include/template_type.hpp")
        << "#error borrowed source directory must precede -iquote "
           "directories\n";
    google::protobuf::ListValue entries;
    int profile = 17;
    for (const auto *file : {"../src/z.cpp", "../src/a.cpp"}) {
      auto &fields =
          *entries.add_values()->mutable_struct_value()->mutable_fields();
      fields["directory"].set_string_value(
          (directory.path() / "build").string());
      fields["file"].set_string_value(file);
      auto *arguments = fields["arguments"].mutable_list_value();
      for (const auto &arg : std::vector<std::string>{
               "clang++", "-std=c++20", "-Iinclude", "-iquote", "include",
               "-DPROFILE=" + std::to_string(profile++), "-c", "-o", "unused.o",
               "-MMD", "-MF", "unused.d", "--", file})
        arguments->add_values()->set_string_value(arg);
    }
    std::string json;
    ASSERT_TRUE(
        google::protobuf::util::MessageToJsonString(entries, &json).ok());
    std::ofstream(directory.path() / "compile_commands.json") << json;
  }

  ParseRequest snippet(std::string code) {
    ParseRequest request;
    request.set_working_directory(directory.path().string());
    request.mutable_cpp_snippet()->set_code(std::move(code));
    return request;
  }

  MatchReply match(const ParseResponse &tree, const std::string &query,
                   const std::string &scope_id = {}) {
    MatchRequest request;
    request.set_query(query);
    request.set_resource_scope_id(scope_id);
    request.set_preserve_source(true);
    request.mutable_session()->set_session_id(tree.session_id());
    request.mutable_session()->set_expected_result_revision(
        tree.result_revision());
    return controller->match("owner", request, [] { return true; });
  }
};

TEST_F(CppSnippets, StatementsDefaultCreatesRealSourceAndRetainsDerivedTrees) {
  auto request = snippet("int value = 7;\nvalue += 2;");
  const auto parsed = controller->parse("owner", request, [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  const auto path = std::filesystem::path(parsed.response.source_file());
  EXPECT_EQ(path.extension(), ".cpp");
  EXPECT_TRUE(std::filesystem::is_regular_file(path));
  std::ifstream source(path);
  const std::string text{std::istreambuf_iterator<char>(source), {}};
  EXPECT_NE(text.find("inline void ctk_snippet()"), std::string::npos);
  EXPECT_NE(text.find("value += 2;"), std::string::npos);
  const auto rows =
      match(parsed.response, "varDecl(hasName(\"value\")).bind(\"v\")");
  ASSERT_EQ(rows.code, MatchCode::Ok) << rows.message;
  ASSERT_EQ(rows.response.results_size(), 1);
  const auto &location = rows.response.results(0).bindings().at("v").location();
  EXPECT_EQ(location.file(), path.string());
  EXPECT_EQ(location.line(), 3U);
  EXPECT_EQ(controller->close("owner", parsed.response.session_id()).code,
            MatchCode::Ok);
  CloseFileRequest close;
  close.set_lease_id(parsed.response.file_lease_id());
  CloseFileResponse closed;
  ASSERT_EQ(controller->close_file("owner", close, closed), MatchCode::Ok);
  EXPECT_TRUE(std::filesystem::exists(path));
  PruneCachesRequest prune;
  prune.set_memory(true);
  PruneCachesResponse pruned;
  EXPECT_EQ(controller->prune_caches(prune, pruned).code, MatchCode::Ok);
  EXPECT_TRUE(std::filesystem::exists(path));
  EXPECT_EQ(controller->close("owner", rows.response.session_id()).code,
            MatchCode::Ok);
  controller.reset();
  EXPECT_FALSE(std::filesystem::exists(path));
}

TEST_F(CppSnippets, BorrowsFirstJsonEntryAndInstantiatesTemplateCalls) {
  database();
  auto request = snippet("TemplateType<MyTest> test;\ntest.add(MyTest{});\n"
                         "static_assert(PROFILE == "
                         "17);\nstatic_assert(FROM_RELATIVE_INCLUDE == 23);");
  request.mutable_cpp_snippet()->add_includes("template_type.hpp");
  request.mutable_cpp_snippet()->add_includes("<relative.hpp>");
  const auto parsed = controller->parse("owner", request, [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  const auto calls =
      match(parsed.response, "cxxMemberCallExpr().bind(\"call\")");
  ASSERT_EQ(calls.code, MatchCode::Ok) << calls.message;
  ASSERT_EQ(calls.response.results_size(), 1);
  EXPECT_EQ(calls.response.results(0)
                .bindings()
                .at("call")
                .call_site()
                .static_callee_name(),
            "TemplateType<MyTest>::add");
  const auto methods =
      match(parsed.response, "cxxMethodDecl(isDefinition(), isInstantiated(), "
                             "hasName(\"add\")).bind(\"method\")");
  ASSERT_EQ(methods.code, MatchCode::Ok) << methods.message;
  EXPECT_EQ(methods.response.results_size(), 1);
  EXPECT_FALSE(std::filesystem::exists(directory.path() / "build/unused.o"));
  EXPECT_FALSE(std::filesystem::exists(directory.path() / "build/unused.d"));
}

TEST_F(CppSnippets, ExplicitFileAndAppendedFlagsOverrideFirstCommand) {
  database();
  auto request =
      snippet("static_assert(PROFILE == 31); int selected = PROFILE;");
  request.mutable_cpp_snippet()->set_settings_file("src/a.cpp");
  request.add_compile_arguments("-UPROFILE");
  request.add_compile_arguments("-DPROFILE=31");
  const auto parsed = controller->parse("owner", request, [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  const auto rows =
      match(parsed.response, "varDecl(hasName(\"selected\")).bind(\"v\")");
  ASSERT_EQ(rows.code, MatchCode::Ok) << rows.message;
  EXPECT_EQ(rows.response.results_size(), 1);
}

TEST_F(CppSnippets, FirstCCommandTransfersLanguageBeforeExplicitCppOverrides) {
  std::ofstream(directory.path() / "donor.c") << "int donor;";
  std::ofstream(directory.path() / "flags.rsp") << "-std=c17 -DPROFILE=43";
  google::protobuf::ListValue entries;
  auto &fields =
      *entries.add_values()->mutable_struct_value()->mutable_fields();
  fields["directory"].set_string_value(directory.path().string());
  fields["file"].set_string_value("donor.c");
  auto *arguments = fields["arguments"].mutable_list_value();
  for (const auto *argument : {"clang", "@flags.rsp", "-c", "--", "donor.c"})
    arguments->add_values()->set_string_value(argument);
  std::string json;
  ASSERT_TRUE(google::protobuf::util::MessageToJsonString(entries, &json).ok());
  std::ofstream(directory.path() / "compile_commands.json") << json;
  auto request =
      snippet("static_assert(PROFILE == 43);\n"
              "auto square = []<class T>(T value) { return value * value; };\n"
              "int cpp_value = square(3);");
  request.add_compile_arguments("-std=c++23");
  auto parsed = controller->parse("owner", request, [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  EXPECT_EQ(match(parsed.response, "varDecl(hasName(\"cpp_value\"))")
                .response.results_size(),
            1);
  request.clear_compile_arguments();
  parsed = controller->parse("owner", request, [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
}

TEST_F(CppSnippets, TranslationUnitAllowsTopLevelTemplatesAndInlineHeaders) {
  auto request = snippet("#include <type_traits>\ntemplate<class T> T twice(T "
                         "v) { return v + v; }\n"
                         "int example() { return twice<int>(3); }");
  request.mutable_cpp_snippet()->set_translation_unit(true);
  const auto parsed = controller->parse("owner", request, [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  const auto rows =
      match(parsed.response, "functionDecl(hasName(\"example\")).bind(\"f\")");
  ASSERT_EQ(rows.code, MatchCode::Ok) << rows.message;
  EXPECT_EQ(rows.response.results_size(), 1);
  EXPECT_EQ(match(parsed.response, "functionDecl(hasName(\"ctk_snippet\"))")
                .response.results_size(),
            0);
}

TEST_F(CppSnippets, RejectsInvalidOptionsAndReportsSnippetDiagnosticLines) {
  auto request = snippet("int ok = 1;\nunknown_type fail;");
  auto parsed = controller->parse("owner", request, [] { return true; });
  EXPECT_EQ(parsed.code, MatchCode::InvalidArgument);
  EXPECT_NE(parsed.message.find("snippet.cpp:2:"), std::string::npos)
      << parsed.message;
  request = snippet("int ok;");
  request.mutable_cpp_snippet()->add_includes("header.hpp\n#error injected");
  EXPECT_EQ(controller->parse("owner", request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  request = snippet("int ok;");
  request.mutable_cpp_snippet()->set_settings_file("missing.cpp");
  EXPECT_EQ(controller->parse("owner", request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  request = snippet("int ok;");
  request.set_file_path("fixture.cpp");
  EXPECT_EQ(controller->parse("owner", request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  EXPECT_EQ(
      controller->parse("owner", snippet("int ok;"), [] { return false; }).code,
      MatchCode::Cancelled);
}

TEST_F(CppSnippets, GeneratedWrapperAcceptsStrictProjectWarningFlags) {
  auto request = snippet("int value = 7; (void)value;");
  for (const auto *flag : {"-Werror", "-Wmissing-prototypes", "-Wmissing-declarations",
                            "-Wunused-function", "-Wreserved-identifier"})
    request.add_compile_arguments(flag);
  const auto parsed = controller->parse("owner", request, [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
}

TEST_F(CppSnippets, GeneratedSourcesJoinExistingScopeAndReleaseWithIt) {
  database();
  OpenResourceScopeRequest open;
  open.set_transient(true);
  auto *input = open.add_inputs();
  input->set_file_path("src/z.cpp");
  input->mutable_profile()->set_working_directory(directory.path().string());
  ResourceScopeInfo scope;
  std::string message;
  ASSERT_EQ(controller->open_resource_scope("owner", open, scope, message),
            MatchCode::Ok)
      << message;
  auto request = snippet("int scoped_value = 17;");
  request.set_resource_scope_id(scope.resource_scope_id());
  const auto parsed = controller->parse("owner", request, [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  EXPECT_TRUE(std::filesystem::exists(parsed.response.source_file()));
  const auto rows =
      match(parsed.response, "varDecl(hasName(\"scoped_value\")).bind(\"v\")",
             scope.resource_scope_id());
  ASSERT_EQ(rows.code, MatchCode::Ok) << rows.message;
  EXPECT_EQ(rows.response.results_size(), 1);
  ResourceScopeInfo released;
  ASSERT_EQ(controller->release_resource_scope(
                "owner", scope.resource_scope_id(), released),
            MatchCode::Ok);
  EXPECT_TRUE(released.cleanup_acknowledged());
  EXPECT_FALSE(std::filesystem::exists(parsed.response.source_file()));
}

#ifdef CTK_BUILD_SCRIPT
TEST_F(CppSnippets, NativeScriptsBorrowSettingsAndComposeTemplateAnalysis) {
  database();
  ScriptController scripts;
  ctk::analysis::v1::ScriptRequest request;
  request.mutable_profile()->set_working_directory(directory.path().string());
  request.set_source(R"script(
    let options = {"file": "src/a.cpp", "includes": ["template_type.hpp"],
                   "compile_arguments": ["-UPROFILE", "-DPROFILE=31"]};
    let tree = parse cpp`TemplateType<MyTest> test;
                        test.add(MyTest{});
                        static_assert(PROFILE == 31);` using options;
    let calls = match cxxMemberCallExpr().bind("call") in tree;
    emit count(calls);
  )script");
  const auto result = scripts.run(request, [] { return true; });
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 1);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 1);

  request.set_source(R"script(
    let tree = parse cpp`static_assert(PROFILE == 17); int value;`;
    let rows = match varDecl(hasName("value")).bind("v") in tree;
    emit count(rows);
  )script");
  const auto first = scripts.run(request, [] { return true; });
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  EXPECT_EQ(first.response.emissions(0).value().scalar().integer(), 1);

  request.mutable_profile()->set_frozen(true);
  request.mutable_profile()->set_compilation_database(
      (directory.path() / "compile_commands.json").string());
  request.mutable_profile()->add_compile_arguments("-DPROFILE=17");
  request.mutable_profile()->add_compile_arguments("-std=c++20");
  request.set_source(R"script(
    let tree = parse cpp`static_assert(PROFILE == 18); int selected;` using "src/a.cpp";
    let rows = match varDecl(hasName("selected")).bind("v") in tree;
    emit count(rows);
  )script");
  const auto borrowed = scripts.run(request, [] { return true; });
  ASSERT_EQ(borrowed.code, MatchCode::Ok) << borrowed.message;
  EXPECT_EQ(borrowed.response.emissions(0).value().scalar().integer(), 1);
  request.set_source(R"script(
    let tree = parse cpp`static_assert(PROFILE == 31); int selected;`
      using {"file": "src/a.cpp", "compile_arguments": ["-UPROFILE", "-DPROFILE=31"]};
    let rows = match varDecl(hasName("selected")).bind("v") in tree;
    emit count(rows);
  )script");
  const auto overridden = scripts.run(request, [] { return true; });
  ASSERT_EQ(overridden.code, MatchCode::Ok) << overridden.message;
  EXPECT_EQ(overridden.response.emissions(0).value().scalar().integer(), 1);
}

TEST_F(CppSnippets, NativeScriptGeneratedSourcesUseTheCurrentResourceScope) {
  database();
  OpenResourceScopeRequest open;
  open.set_transient(true);
  auto *input = open.add_inputs();
  input->set_file_path("src/z.cpp");
  input->mutable_profile()->set_working_directory(directory.path().string());
  ResourceScopeInfo scope;
  std::string message;
  ASSERT_EQ(controller->open_resource_scope("owner", open, scope, message),
            MatchCode::Ok)
      << message;
  CursorSettings settings;
  settings.resources = controller->resource_manager();
  ScriptController scripts(settings);
  ctk::analysis::v1::ScriptRequest request;
  request.set_resource_scope_id(scope.resource_scope_id());
  request.mutable_profile()->set_working_directory(directory.path().string());
  request.set_source(R"script(
    let tree = parse cpp`int scoped_value = PROFILE;` using "src/z.cpp";
    let rows = match varDecl(hasName("scoped_value")).bind("v") in tree;
    emit count(rows);
  )script");
  const auto result = scripts.run(request, [] { return true; }, "owner");
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 1);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 1);
  ResourceScopeInfo released;
  ASSERT_EQ(controller->release_resource_scope(
                "owner", scope.resource_scope_id(), released),
            MatchCode::Ok);
  EXPECT_TRUE(released.cleanup_acknowledged());
}
#endif

TEST(CppSnippetSource, UnpublishedSourceIsRemovedOnFailureOrOwnerRelease) {
  ParseRequest request;
  request.mutable_cpp_snippet()->set_code("int item;");
  std::filesystem::path path;
  {
    const auto source = ctk::clang_layer::prepare_cpp_snippet(request);
    path = source.request.file_path();
    EXPECT_TRUE(std::filesystem::is_regular_file(path));
  }
  EXPECT_FALSE(std::filesystem::exists(path));
}
} // namespace
} // namespace ctk::application
