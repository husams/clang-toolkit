#include "ctk/application/script_controller.hpp"
#include "ctk/clang/tooling.hpp"
#include <filesystem>
#include <fstream>
#include <gtest/gtest.h>
#ifdef CTK_WITH_CLANG
#include "ctk/platform/temporary_directory.hpp"
#endif
namespace ctk::application {
using Code = ctk::clang_layer::MatchCode;
TEST(ScriptController, PureScriptsAndArgumentValidation) {
  CursorSettings settings;
  settings.workers = 1;
  ScriptController controller(settings);
  ctk::analysis::v1::ScriptRequest request;
  request.set_source("emit 7;");
  auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 7);
  request.set_source("emit nonexistent();");
  EXPECT_EQ(controller.run(request, [] { return true; }).code,
            Code::InvalidArgument);
  request.set_source("emit match(\"functionDecl()\");");
  EXPECT_EQ(controller.run(request, [] { return true; }).code,
            Code::InvalidArgument);
  request.set_max_steps(0);
  EXPECT_EQ(controller.run(request, [] { return true; }).code,
            Code::InvalidArgument);
}
TEST(ScriptController, RejectsInvalidCompilationProfilesBeforeExecution) {
  ScriptController controller;
  ctk::analysis::v1::ScriptRequest request;
  request.set_source("emit 1;");
  request.mutable_profile()->set_working_directory("relative/path");
  EXPECT_EQ(controller.run(request, [] { return true; }).code,
            Code::InvalidArgument);
  request.mutable_profile()->set_working_directory(
      std::filesystem::current_path().string());
  request.mutable_profile()->add_compile_arguments("-c");
  EXPECT_EQ(controller.run(request, [] { return true; }).code,
            Code::InvalidArgument);
}
#ifndef CTK_WITH_CLANG
TEST(ScriptController, NativeOperationsFailExplicitlyWhenClangIsDisabled) {
  ScriptController controller;
  ctk::analysis::v1::ScriptRequest request;
  request.set_source("emit callgraph();");
  request.mutable_file()->set_file_path("file.cc");
  request.mutable_file()->set_working_directory(
      std::filesystem::current_path().string());
  EXPECT_EQ(controller.run(request, [] { return true; }).code,
            Code::FailedPrecondition);
}
#else
class ScriptNative : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory directory{"ctk-script"};
  ctk::analysis::v1::ScriptRequest request;
  void SetUp() override {
    std::ofstream(directory.path() / "fixture.cc")
        << "int g(){return 7;} int f(){return g()+8;}";
    request.mutable_file()->set_file_path("fixture.cc");
    request.mutable_file()->set_working_directory(directory.path().string());
  }
};
TEST_F(ScriptNative, ComposesEveryNativeOperationOnOneWorker) {
  CursorSettings settings;
  settings.workers = 1;
  ScriptController controller(settings);
  request.set_source(R"script(
    let rows=match("functionDecl(isDefinition()).bind(\"f\")");
  emit count(rows);
  foreach
    item in rows { emit continue(item, "f", "integerLiteral().bind(\"n\")"); }
  emit continue(rows, "f", "functionDecl().bind(\"f\")", scope = "root");
  emit restart(rows, "callExpr().bind(\"call\")");
  emit traverse(max_depth = 0);
  emit cfg("f", always_add_statements = true);
  emit callgraph();
  )script");
  auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 8);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 2);
  EXPECT_EQ(result.response.emissions(1).value().matches().rows_size(), 1);
  EXPECT_EQ(result.response.emissions(2).value().matches().rows_size(), 1);
  EXPECT_EQ(result.response.emissions(3).value().matches().rows_size(), 2);
  EXPECT_EQ(result.response.emissions(4).value().matches().rows_size(), 1);
  EXPECT_EQ(result.response.emissions(5).value().traversal().nodes_size(), 1);
  EXPECT_EQ(result.response.emissions(6).value().cfg().graphs_size(), 1);
  EXPECT_EQ(result.response.emissions(7).value().call_graph().nodes_size(), 3);
}
TEST_F(ScriptNative, BranchesFromImmutableRowsAndPreservesRowSelection) {
  ScriptController controller;
  request.set_source(
      R"script(let rows=match("functionDecl(isDefinition()).bind(\"f\")");
  let selected = row(rows, 0);
  emit continue(selected, "f", "integerLiteral().bind(\"n\")");
  emit continue(selected, "f", "integerLiteral().bind(\"n\")");
  emit rows;)script");
  auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  EXPECT_EQ(result.response.emissions(0).value().SerializeAsString(),
            result.response.emissions(1).value().SerializeAsString());
  EXPECT_EQ(result.response.emissions(2).value().matches().rows_size(), 2);
}
TEST_F(ScriptNative, NativeAndScopeFailuresAreAtomic) {
  ScriptController controller;
  for (const auto &source :
       {"emit 7; emit cfg(\"missing\");",
        "let rows=match(\"functionDecl()\"); foreach item in rows {let "
        "local=1;} emit local;",
        "emit 7; emit traverse(max_nodes=1);", "emit cfg(\"f\",max_blocks=0);",
        "emit cfg(\"f\",add_scopes=1);", "emit callgraph(unknown=true);",
        "emit traverse(max_depth=257);"}) {
    request.set_source(source);
    auto result = controller.run(request, [] { return true; });
    EXPECT_NE(result.code, Code::Ok) << source;
    EXPECT_EQ(result.response.emissions_size(), 0);
  }
}
class MutatingQueryEngine final : public ctk::clang_layer::IQueryEngine {
public:
  std::shared_ptr<IQueryEngine> inner = ctk::clang_layer::make_query_engine();
  std::filesystem::path file;
  int acquisitions = 0;
  ctk::cache::SnapshotPtr
  acquire_snapshot(const ctk::clang_layer::FileInput &input) override {
    ++acquisitions;
    auto snapshot = inner->acquire_snapshot(input);
    std::ofstream(file) << "int replacement(){return 99;}";
    return snapshot;
  }
  ctk::clang_layer::QueryResult match(const ctk::clang_layer::FileInput &input,
                                      const std::string &query,
                                      const Checkpoint &check,
                                      const MatchCallback &callback) override {
    return inner->match(input, query, check, callback);
  }
};
TEST_F(ScriptNative, AllOperationsPinTheSameGenerationDespiteFileChanges) {
  auto engine = std::make_shared<MutatingQueryEngine>();
  engine->file = directory.path() / "fixture.cc";
  ScriptController controller({}, engine);
  request.set_source(R"script(emit match("functionDecl().bind(\"f\")");
  emit cfg("f");
  emit callgraph();)script");
  auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  EXPECT_EQ(engine->acquisitions, 1);
  EXPECT_EQ(result.response.emissions(1)
                .value()
                .cfg()
                .graphs(0)
                .function()
                .qualified_name(),
            "f");
  ctk::analysis::v1::ScriptRequest second = request;
  second.set_source("emit cfg(\"replacement\");");
  EXPECT_EQ(controller.run(second, [] { return true; }).code, Code::Ok);
  EXPECT_EQ(engine->acquisitions, 2);
}
TEST_F(ScriptNative, SnapshotAndResponseBoundsPublishNoEmissions) {
  CursorSettings settings;
  settings.max_memory_bytes = 1;
  ScriptController tiny_snapshot(settings);
  request.set_source("emit callgraph();");
  auto result = tiny_snapshot.run(request, [] { return true; });
  EXPECT_EQ(result.code, Code::ResourceExhausted) << result.message;
  settings = {};
  settings.results.max_bytes = 1;
  ScriptController tiny_response(settings);
  result = tiny_response.run(request, [] { return true; });
  EXPECT_EQ(result.code, Code::ResourceExhausted);
  EXPECT_EQ(result.response.emissions_size(), 0);
}
TEST_F(ScriptNative, ParsesTreesAndMatchesNativeBindingExpressions) {
  ScriptController controller;
  request.set_source(R"script(
    let tree = parse "fixture.cc";
    let functions = match functionDecl(isDefinition()).bind("f") in $tree;
    let calls = match callExpr().bind("call") in $functions.f;
    let n = match integerLiteral().bind("n") in "fixture.cc";
    let first = match integerLiteral().bind("n") in $functions[0].f;
    emit tree;
    emit count(functions);
    emit count(calls);
    emit count(n);
    emit count(first);
    emit functions;
  )script");
  const auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 6);
  EXPECT_EQ(result.response.emissions(0).value().tree().file().file_path(),
            "fixture.cc");
  EXPECT_EQ(result.response.emissions(1).value().scalar().integer(), 2);
  EXPECT_EQ(result.response.emissions(2).value().scalar().integer(), 1);
  EXPECT_EQ(result.response.emissions(3).value().scalar().integer(), 2);
  EXPECT_EQ(result.response.emissions(4).value().scalar().integer(), 1);
  EXPECT_EQ(result.response.emissions(5).value().matches().rows_size(), 2);
}
TEST_F(ScriptNative, YieldsNativeBindingsBeyondLexicalScope) {
  ScriptController controller;
  request.set_source(R"script(
    let functions = 7;
    let analysis = in parse "fixture.cc" {
      let functions = match functionDecl(isDefinition()).bind("f");
      let calls = match callExpr().bind("call") in $functions.f;
      yield calls;
    };
    let more = match declRefExpr().bind("ref") in $analysis.call;
    emit more;
    emit functions;
    emit analysis;
  )script");
  const auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 3);
  EXPECT_EQ(result.response.emissions(0).value().matches().rows_size(), 1);
  EXPECT_EQ(result.response.emissions(1).value().scalar().integer(), 7);
  EXPECT_EQ(result.response.emissions(2).value().matches().rows_size(), 1);
}
TEST_F(ScriptNative, ScopedLegacyMatchOptionsUseBlockTreeAndRestoreDefault) {
  std::ofstream(directory.path() / "second.cc") << "int second(){return 9;}";
  ScriptController controller;
  request.set_source(R"script(
    let selected = in parse "second.cc" {
      yield match("functionDecl()", traversal="spelled");
    };
    emit count(selected);
    emit count(match("functionDecl()", traversal="spelled"));
  )script");
  const auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 2);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 1);
  EXPECT_EQ(result.response.emissions(1).value().scalar().integer(), 2);
}
TEST_F(ScriptNative, ScopedLegacyMatchOptionsWorkWithoutRequestDefault) {
  ScriptController controller;
  request.clear_file();
  request.set_source("let selected = in parse \"" +
                     (directory.path() / "fixture.cc").string() +
                     R"script(" { yield match("functionDecl()",
                         traversal="spelled");
                     }; emit count(selected);)script");
  const auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 1);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 2);
}
TEST_F(ScriptNative, ScopedLegacyMatchOptionsKeepValidationAndResultLimits) {
  ScriptController controller;
  for (const auto &option :
       {"traversal=\"invalid\"", "traversal=true", "scope=\"root\""}) {
    request.set_source(
        std::string("emit 1; let selected = in parse \"fixture.cc\" {") +
        " yield match(\"functionDecl()\", " + option + "); }; emit selected;");
    const auto result = controller.run(request, [] { return true; });
    EXPECT_EQ(result.code, Code::InvalidArgument) << result.message;
    EXPECT_EQ(result.response.emissions_size(), 0);
  }
  CursorSettings settings;
  settings.results.max_rows = 1;
  ScriptController limited(settings);
  request.set_source(R"script(
    emit 1;
    let selected = in parse "fixture.cc" {
      yield match("functionDecl()", traversal="spelled");
    };
    emit selected;
  )script");
  const auto result = limited.run(request, [] { return true; });
  EXPECT_EQ(result.code, Code::ResourceExhausted) << result.message;
  EXPECT_EQ(result.response.emissions_size(), 0);
}
TEST_F(ScriptNative, ExplicitParseUsesProfileWithoutDefaultFile) {
  const auto profile_directory = directory.path() / "profile";
  std::filesystem::create_directories(profile_directory);
  std::ofstream(profile_directory / "profile.cc")
      << "#ifndef SCRIPT_PROFILE_FLAG\n#error missing profile flag\n#endif\n"
         "int selected(){return 1;}\n";
  request.clear_file();
  request.mutable_profile()->set_working_directory(
      profile_directory.string());
  request.mutable_profile()->add_compile_arguments("-DSCRIPT_PROFILE_FLAG");
  request.set_source(R"script(
    let tree = parse "profile.cc";
    let parsed = match functionDecl(hasName("selected")) in $tree;
    let explicit = match functionDecl(hasName("selected")) in "profile.cc";
    emit count(parsed);
    emit count(explicit);
  )script");
  ScriptController controller;
  const auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 2);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 1);
  EXPECT_EQ(result.response.emissions(1).value().scalar().integer(), 1);
}
TEST_F(ScriptNative, ContinueRejectsUnsupportedBindingScopeAndMissingBind) {
  std::ofstream(directory.path() / "fixture.cc")
      << "struct B {}; struct D : B {};";
  ScriptController controller;
  request.set_source(R"script(
    let rows = match cxxRecordDecl(hasName("D"),
      hasAnyBase(cxxBaseSpecifier().bind("base"))).bind("record");
    emit continue(rows, "base", "decl()", scope = "root");
  )script");
  auto result = controller.run(request, [] { return true; });
  EXPECT_EQ(result.code, Code::FailedPrecondition) << result.message;
  EXPECT_EQ(result.response.emissions_size(), 0);

  request.set_source(R"script(
    let rows = match cxxRecordDecl().bind("record");
    emit continue(rows, "missing", "decl()", scope = "root");
  )script");
  result = controller.run(request, [] { return true; });
  EXPECT_EQ(result.code, Code::NotFound) << result.message;
  EXPECT_EQ(result.response.emissions_size(), 0);
}
TEST_F(ScriptNative, EmptyBindingCollectionsContinueAndSelectionMissesFail) {
  ScriptController controller;
  request.set_source(R"script(
    let tree = parse "fixture.cc";
    let none = match cxxRecordDecl().bind("record") in $tree;
    let next = match fieldDecl().bind("field") in $none.record;
    let again = match integerLiteral().bind("n") in $next.field;
    emit count(again);
  )script");
  auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 0);
  for (
      const auto &source :
      {R"(let f = match functionDecl().bind("f") in "fixture.cc"; emit match callExpr() in $f.missing;)",
       R"(let f = match functionDecl().bind("f") in "fixture.cc"; emit match callExpr() in $f[2].f;)",
       R"(let f = match cxxRecordDecl().bind("f") in "fixture.cc"; emit match callExpr() in $f[0].f;)",
       R"(let tree = parse "fixture.cc"; emit match imaginaryMatcher() in $tree;)",
       R"(let analysis = in parse "fixture.cc" { let local = 1; yield local; }; emit local;)"}) {
    request.set_source(source);
    result = controller.run(request, [] { return true; });
    EXPECT_NE(result.code, Code::Ok) << source;
    EXPECT_EQ(result.response.emissions_size(), 0);
  }
}
TEST_F(ScriptNative,
       ExplicitFilesWorkWithoutRequestDefaultsAndStayIndependent) {
  std::ofstream(directory.path() / "second.cc") << "int second(){return 9;}";
  ScriptController controller;
  request.clear_file();
  request.set_source(
      "let first = parse \"" + (directory.path() / "fixture.cc").string() +
      "\"; let second = parse \"" + (directory.path() / "second.cc").string() +
      R"("; emit count(match functionDecl() in $first); emit count(match functionDecl() in $second); emit count(match functionDecl() in $first);)");
  const auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 3);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 2);
  EXPECT_EQ(result.response.emissions(1).value().scalar().integer(), 1);
  EXPECT_EQ(result.response.emissions(2).value().scalar().integer(), 2);
}
TEST_F(ScriptNative, ParseAndScopedMatchingPinOneGeneration) {
  auto engine = std::make_shared<MutatingQueryEngine>();
  engine->file = directory.path() / "fixture.cc";
  ScriptController controller({}, engine);
  request.set_source(R"script(
    let tree = parse "fixture.cc";
    let analysis = in $tree {
      let functions = match functionDecl(isDefinition()).bind("f");
      yield functions;
    };
    emit count(match callExpr().bind("call") in $analysis.f);
    emit count(match integerLiteral().bind("n") in $tree);
  )script");
  const auto result = controller.run(request, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  EXPECT_EQ(engine->acquisitions, 1);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 1);
  EXPECT_EQ(result.response.emissions(1).value().scalar().integer(), 2);
}
#endif
} // namespace ctk::application
