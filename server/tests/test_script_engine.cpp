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
TEST(ScriptEngine, CollectionsForeachAndGroupingAreTypedValues) {
  auto result = Engine{}.run(R"script(
    let settings = {"answer": 42, labels: ["first", "second"]};
    let labels = foreach label in $settings.labels do { $label; };
    let wrapped = ($labels);
    emit $settings.answer;
    emit $wrapped[1];
  )script");
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 2);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 42);
  EXPECT_EQ(result.response.emissions(1).value().scalar().text(), "second");
}
TEST(ScriptEngine, StatementForeachCollectsListValues) {
  const auto result = Engine{}.run(
      "foreach value in [7, \"eight\"] do { $value; };", nullptr, {},
      [] { return true; }, {}, {}, true);
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 1);
  ASSERT_EQ(result.response.emissions(0).name(), "__final__");
  const auto &values = result.response.emissions(0).value().list().values();
  ASSERT_EQ(values.size(), 2);
  EXPECT_EQ(values.Get(0).scalar().integer(), 7);
  EXPECT_EQ(values.Get(1).scalar().text(), "eight");
}
TEST(ScriptEngine, StatementForeachHandlesEmptyAndNestedLists) {
  const auto empty = Engine{}.run("foreach value in [] do { $value; };",
                                  nullptr, {}, [] { return true; }, {}, {},
                                  true);
  ASSERT_EQ(empty.code, Code::Ok) << empty.message;
  ASSERT_EQ(empty.response.emissions_size(), 1);
  EXPECT_TRUE(empty.response.emissions(0).value().list().values().empty());

  const auto nested = Engine{}.run(
      "foreach outer in [[1, 2], [3]] do { "
      "foreach inner in $outer do { $inner; }; };",
      nullptr, {}, [] { return true; }, {}, {}, true);
  ASSERT_EQ(nested.code, Code::Ok) << nested.message;
  ASSERT_EQ(nested.response.emissions_size(), 1);
  const auto &groups = nested.response.emissions(0).value().list().values();
  ASSERT_EQ(groups.size(), 2);
  ASSERT_EQ(groups.Get(0).list().values_size(), 2);
  EXPECT_EQ(groups.Get(0).list().values(0).scalar().integer(), 1);
  EXPECT_EQ(groups.Get(0).list().values(1).scalar().integer(), 2);
  ASSERT_EQ(groups.Get(1).list().values_size(), 1);
  EXPECT_EQ(groups.Get(1).list().values(0).scalar().integer(), 3);
}
TEST(ScriptEngine, FlattenRecursesThroughNestedCollections) {
  auto result = Engine{}.run("emit flatten([[1, [2]], [3]]);");
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 1);
  const auto &values = result.response.emissions(0).value().list().values();
  ASSERT_EQ(values.size(), 3);
  EXPECT_EQ(values.Get(0).scalar().integer(), 1);
  EXPECT_EQ(values.Get(1).scalar().integer(), 2);
  EXPECT_EQ(values.Get(2).scalar().integer(), 3);
}
TEST(ScriptEngine, FinalValueUsesDetachedSentinelOnlyWhenRequested) {
  auto collected = Engine{}.run(
      "let answer = 42;", nullptr, {}, [] { return true; }, {}, {}, true);
  ASSERT_EQ(collected.code, Code::Ok) << collected.message;
  ASSERT_EQ(collected.response.emissions_size(), 1);
  EXPECT_EQ(collected.response.emissions(0).name(), "__final__");
  auto normal = Engine{}.run("let answer = 42;");
  ASSERT_EQ(normal.code, Code::Ok) << normal.message;
  EXPECT_EQ(normal.response.emissions_size(), 0);
}
TEST(ScriptEngine, BatchClassificationFollowsParsedSyntax) {
  Engine engine;
  EXPECT_FALSE(engine.contains_batch("emit \"batch part in $inputs size 1 do "
                                     "{}\"; // batch fake in comment\n"));
  EXPECT_TRUE(engine.contains_batch("let report = batch part in $inputs size 1 "
                                    "do { count($part.inputs); };"));
}
class ReservedWordEnvironment final : public Environment {
public:
  std::string called;
  Value call(const std::string &name, const std::vector<Value> &,
             const std::map<std::string, Value> &) override {
    called = name;
    auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
    wire->mutable_scalar()->set_integer(9);
    return {wire, {}, {}};
  }
};
TEST(ScriptEngine, BatchPolicyWordsRemainCollectionNamesAndCalls) {
  ReservedWordEnvironment environment;
  const auto result = Engine{}.run("let values = {count: 3, continue: 4}; "
                                   "emit values.count; emit values.continue; "
                                   "emit count([1, 2]); emit continue(1);",
                                   &environment);
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 4);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 3);
  EXPECT_EQ(result.response.emissions(1).value().scalar().integer(), 4);
  EXPECT_EQ(result.response.emissions(2).value().scalar().integer(), 2);
  EXPECT_EQ(result.response.emissions(3).value().scalar().integer(), 9);
  EXPECT_EQ(environment.called, "continue");
}
class LegacyBindingEnvironment final : public Environment {
public:
  std::string observed_binding;
  Value call(const std::string &, const std::vector<Value> &,
             const std::map<std::string, Value> &) override {
    throw Error(Code::InvalidArgument, "unexpected script function");
  }
  Value match(const std::string &, const Value *target,
              const std::string &binding) override {
    if (!target || !target->wire || !target->wire->has_matches())
      throw Error(Code::InvalidArgument, "expected rows target");
    observed_binding = binding;
    auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
    wire->mutable_matches()->add_rows();
    return {wire, {}, {}};
  }
};
TEST(ScriptEngine, LegacyMatchMemberTargetStillSelectsBinding) {
  LegacyBindingEnvironment environment;
  ctk::analysis::v1::ScriptValue rows;
  rows.mutable_matches()->add_rows();
  std::map<std::string, ctk::analysis::v1::ScriptValue> initial{{"rows", rows}};
  auto result = Engine{}.run(
      "emit match functionDecl() in $rows.f;", &environment, {},
      [] { return true; }, initial);
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  EXPECT_EQ(environment.observed_binding, "f");
  ASSERT_EQ(result.response.emissions_size(), 1);
  EXPECT_EQ(result.response.emissions(0).value().matches().rows_size(), 1);
}

class BatchEnvironment final : public Environment {
public:
  std::vector<std::size_t> group_sizes;
  std::size_t closed_groups = 0;
  std::size_t file_count = 3;
  Value call(const std::string &, const std::vector<Value> &,
             const std::map<std::string, Value> &) override {
    throw Error(Code::InvalidArgument, "unexpected script function");
  }
  Value files(const std::string &) override {
    auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
    wire->mutable_files();
    for (std::size_t i = 0; i < file_count; ++i)
      wire->mutable_files()->add_inputs()->set_file_path("fixture" +
                                                         std::to_string(i));
    return {wire, {}, {}};
  }
  Value match(const std::string &, const Value *target, const std::string &,
              const std::map<std::string, Value> &) override {
    if (!target || !target->wire->has_files())
      throw Error(Code::InvalidArgument, "expected file manifest target");
    auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
    for (std::size_t i = 0;
         i < static_cast<std::size_t>(target->wire->files().inputs_size()); ++i)
      wire->mutable_matches()->add_rows();
    return {wire, {}, {}};
  }
  void begin_batch_group(const Value &group, std::size_t, std::size_t,
                         std::uint64_t) override {
    group_sizes.push_back(static_cast<std::size_t>(
        group.wire->object().fields().at("inputs").files().inputs_size()));
  }
  void end_batch_group(bool) override { ++closed_groups; }
};

TEST(ScriptEngine, NativeBatchCollectsDetachedValuesAndUsesExactOptions) {
  BatchEnvironment environment;
  std::vector<std::string> saved;
  auto result = Engine{}.run(
      R"script(
    let inputs = files "fixture";
    let collected = batch part in $inputs size 2 jobs 1 memory "1MiB" on error continue do {
      let count_value = count($part.inputs);
      let rows = match functionDecl().bind("f") in $part.inputs;
      save $rows to "group-${part.index}.json" as json;
      $rows;
    };
    emit $collected.status;
    emit count($collected.results);
    emit $collected.results[0];
  )script",
      &environment, {}, [] { return true; }, {},
      [&saved](const auto &path, const auto &, const auto &format) {
        EXPECT_EQ(format, "json");
        saved.push_back(path);
        return std::pair{Code::Ok, std::string{}};
      });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(environment.group_sizes, (std::vector<std::size_t>{2, 1}));
  EXPECT_EQ(environment.closed_groups, 2U);
  ASSERT_EQ(saved, (std::vector<std::string>{"group-1.json", "group-2.json"}));
  ASSERT_EQ(result.response.emissions_size(), 3);
  EXPECT_EQ(result.response.emissions(0).value().scalar().text(), "completed");
  EXPECT_EQ(result.response.emissions(1).value().scalar().integer(), 2);
  EXPECT_EQ(result.response.emissions(2).value().matches().rows_size(), 2);
}
TEST(ScriptEngine, BatchBodyKeywordsDoNotChangeItsHeaderPolicy) {
  BatchEnvironment environment;
  auto result = Engine{}.run(R"script(
    let inputs = files "fixture";
    let report = batch part in $inputs size 1 do {
      let group_count = count($part.inputs);
      fail(1);
      $group_count;
    };
    emit $report.failed_groups;
    emit $report.skipped_groups;
  )script",
                             &environment, {}, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  EXPECT_EQ(environment.group_sizes, (std::vector<std::size_t>{1}));
  EXPECT_EQ(environment.closed_groups, 1U);
  ASSERT_EQ(result.response.emissions_size(), 2);
  EXPECT_EQ(result.response.emissions(0).value().scalar().integer(), 1);
  EXPECT_EQ(result.response.emissions(1).value().scalar().integer(), 2);
}
TEST(ScriptEngine, EmptyManifestAllowsOnlyZeroCountBatches) {
  BatchEnvironment environment;
  environment.file_count = 0;
  auto result = Engine{}.run(R"script(
    let inputs = files "fixture";
    let report = batch part in $inputs count 0 do { 1; };
    emit $report.status;
    emit $report.results_complete;
    emit $report.completed_groups;
  )script",
                             &environment, {}, [] { return true; });
  ASSERT_EQ(result.code, Code::Ok) << result.message;
  ASSERT_EQ(result.response.emissions_size(), 3);
  EXPECT_EQ(result.response.emissions(0).value().scalar().text(), "completed");
  EXPECT_TRUE(result.response.emissions(1).value().scalar().boolean());
  EXPECT_EQ(result.response.emissions(2).value().scalar().integer(), 0);
  result = Engine{}.run(R"script(
    let inputs = files "fixture";
    let report = batch part in $inputs count 1 do { 1; };
  )script",
                        &environment);
  EXPECT_EQ(result.code, Code::InvalidArgument);
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
