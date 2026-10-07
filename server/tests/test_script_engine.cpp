#include "ctk/script/engine.hpp"
#include "ctk/script/error.hpp"
#include <gtest/gtest.h>
namespace ctk::script {
using Code = ctk::clang_layer::MatchCode;
TEST(ScriptEngine, TypedLiteralsAndAliasesAreExecutedInsteadOfEchoed) {
  auto result = Engine{}.run(
      R"(let x = "hello\n\u03bb"; emit x; emit -9223372036854775808; emit 1.25e2; emit true;)");
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 4);
  EXPECT_EQ(result.response.emissions(0).name(), "x");
  EXPECT_EQ(result.response.emissions(0).value().scalar().text(), "hello\nλ");
  EXPECT_EQ(result.response.emissions(1).value().scalar().integer(), INT64_MIN);
  EXPECT_EQ(result.response.emissions(2).value().scalar().number(), 125);
  EXPECT_TRUE(result.response.emissions(3).value().scalar().boolean());
  EXPECT_NE(Engine{}.eval("emit 7;"), "emit 7;");
}
TEST(ScriptEngine, ParserAndVariableErrorsPublishNoPartialValues) {
  for (const auto &source :
       {"emit 1; emit missing;", "emit 1; let x = ;", "let x=1; let x=2;",
        "emit 9223372036854775808;", "emit 1e999;", "emit \"bad\\q\";",
        "emit count(1);", "emit row(1,0);"}) {
    auto result = Engine{}.run(source);
    EXPECT_EQ(result.code, Code::InvalidArgument)
        << source << ": " << result.message;
    EXPECT_EQ(result.response.emissions_size(), 0);
  }
}
class RecordingEnvironment final : public Environment {
public:
  int calls = 0;
  Value call(const std::string &, const std::vector<Value> &,
             const std::map<std::string, Value> &) override {
    ++calls;
    auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
    wire->mutable_scalar()->set_integer(1);
    return {wire, {}, {}};
  }
};
TEST(ScriptEngine, CompleteSyntaxAndDuplicateOptionsPrecedeNativeEvaluation) {
  RecordingEnvironment environment;
  auto result = Engine{}.run("emit query(); let x=;", &environment);
  EXPECT_EQ(result.code, Code::InvalidArgument);
  EXPECT_EQ(environment.calls, 0);
  result = Engine{}.run("emit query(a=1,a=2);", &environment);
  EXPECT_EQ(result.code, Code::InvalidArgument);
  EXPECT_EQ(environment.calls, 0);
  result = Engine{}.run("emit query(a=1,2);", &environment);
  EXPECT_EQ(result.code, Code::InvalidArgument);
  EXPECT_EQ(environment.calls, 0);
}
TEST(ScriptEngine, StepByteAndCancellationLimitsAreAtomic) {
  Limits limits;
  limits.max_steps = 1;
  auto result = Engine{}.run("emit 1; emit 2;", nullptr, limits);
  EXPECT_EQ(result.code, Code::ResourceExhausted);
  EXPECT_EQ(result.response.emissions_size(), 0);
  limits = {};
  limits.max_response_bytes = 1;
  EXPECT_EQ(Engine{}.run("emit 1;", nullptr, limits).code,
            Code::ResourceExhausted);
  limits = {};
  limits.max_retained_bytes = 1;
  EXPECT_EQ(Engine{}.run("let x=1;", nullptr, limits).code,
            Code::ResourceExhausted);
  int checks = 0;
  result = Engine{}.run("emit 1; emit 2;", nullptr, {},
                        [&] { return ++checks < 4; });
  EXPECT_EQ(result.code, Code::Cancelled);
  EXPECT_EQ(result.response.emissions_size(), 0);
}
TEST(ScriptEngine, NestingAndSourceGuardsPrecedeRecursiveParsing) {
  std::string source = "emit ";
  for (int i = 0; i < 65; ++i)
    source += "count(";
  source += "1";
  source += std::string(65, ')');
  source += ';';
  EXPECT_EQ(Engine{}.run(source).code, Code::ResourceExhausted);
  EXPECT_EQ(Engine{}.run(std::string(1024 * 1024 + 1, ' ')).code,
            Code::ResourceExhausted);
}
class ScriptBindingState final : public ctk::clang_layer::NativeBindingState {
public:
  ctk::cache::SnapshotPtr snapshot() const override { return {}; }
  std::size_t retained_bytes() const override { return 1; }
};
class ScopedEnvironment final : public Environment {
public:
  std::vector<std::string> queries;
  std::vector<std::string> files;
  Value call(const std::string &, const std::vector<Value> &,
             const std::map<std::string, Value> &) override {
    throw Error(Code::InvalidArgument, "unexpected legacy operation");
  }
  Value parse_file(const std::string &file) override {
    files.push_back(file);
    auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
    wire->mutable_tree()->mutable_file()->set_file_path(file);
    return {wire, std::make_shared<ScriptBindingState>(), {}};
  }
  Value match(const std::string &query, const Value *target,
              const std::string &binding) override {
    queries.push_back(query);
    if (!target || !target->wire->has_tree() || !binding.empty())
      throw Error(Code::InvalidArgument, "unexpected native match target");
    auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
    wire->mutable_matches()->add_rows();
    return {wire, target->bindings,
            std::make_shared<const std::vector<std::size_t>>(
                std::vector<std::size_t>{0})};
  }
};
TEST(ScriptEngine, ScopedTreesShadowLocalsRestoreDefaultsAndYieldValues) {
  ScopedEnvironment environment;
  auto result = Engine{}.run(R"script(
    let tree = parse "outer.cc";
    let label = 7;
    let analysis = in $tree {
      let label = 9;
      let inner = in parse "inner.cc" {
        let rows = match functionDecl( isDefinition() ).bind("f");
        yield rows;
      };
      emit label;
      let rows = match callExpr().bind("call");
      yield rows;
    };
    emit label;
    emit count(analysis);
    emit count(match integerLiteral().bind("n") in $tree);
  )script",
                             &environment);
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 4);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 9);
  EXPECT_EQ(result.response.emissions(1).value().scalar().integer(), 7);
  EXPECT_EQ(result.response.emissions(2).value().scalar().integer(), 1);
  EXPECT_EQ(result.response.emissions(3).value().scalar().integer(), 1);
  ASSERT_EQ(environment.queries.size(), 3);
  EXPECT_EQ(environment.queries[0],
            "functionDecl( isDefinition() ).bind(\"f\")");
  EXPECT_EQ(environment.files,
            (std::vector<std::string>{"outer.cc", "inner.cc"}));
}
TEST(ScriptEngine, ScopedBlocksRequireExactlyOneTerminalYieldAndHideLocals) {
  ScopedEnvironment environment;
  for (const auto &source :
       {"let x = in parse \"x.cc\" { let y = 1; };",
        "let x = in parse \"x.cc\" { yield 1; yield 2; };",
        "let x = in parse \"x.cc\" { yield 1; emit 2; };", "yield 1;",
        "let x = in parse \"x.cc\" { let hidden=1; yield hidden; }; emit "
        "hidden;",
        "let x = in 7 { yield 1; };",
        "emit 1; let x = in parse \"x.cc\" { emit 2; yield missing; };",
        "emit match functionDecl() in $x[-1].f;",
        "emit match functionDecl() in $x[1.5].f;"}) {
    auto result = Engine{}.run(source, &environment);
    EXPECT_EQ(result.code, Code::InvalidArgument)
        << source << ": " << result.message;
    EXPECT_EQ(result.response.emissions_size(), 0);
  }
}
} // namespace ctk::script
