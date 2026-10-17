#include "ctk/application/cfg_controller.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <gtest/gtest.h>

namespace ctk::application {
namespace {
namespace pb = ctk::analysis::v1;
using ctk::clang_layer::MatchCode;
class VariableFlow : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory directory{"ctk-variable-flow"};
  MatchController matches;
  CfgController cfg{{}, {}, {}, &matches};
  pb::VariableFlowRequest request;
  std::vector<pb::VariableFlowEvent> events;
  void select(const std::string &body, const std::string &standard = "c++20",
              const std::string &triple = {}) {
    std::ofstream(directory.path() / "flow.cc") << body;
    ctk::match::v1::MatchRequest target;
    target.mutable_file()->set_file_path("flow.cc");
    target.mutable_file()->set_working_directory(directory.path().string());
    target.mutable_file()->add_compile_arguments("-std=" + standard);
    if (!triple.empty())
      target.mutable_file()->add_compile_arguments("--target=" + triple);
    target.set_query("varDecl(hasName(\"x\"), "
                     "hasAncestor(functionDecl(hasName(\"example\")).bind("
                     "\"f\"))).bind(\"v\")");
    target.set_preserve_source(true);
    auto result = matches.match("owner", target, [] { return true; });
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    ASSERT_GT(result.response.results_size(), 0);
    for (auto *binding :
         {request.mutable_variable(), request.mutable_function()}) {
      binding->set_session_id(result.response.session_id());
      binding->set_expected_result_revision(result.response.result_revision());
      binding->set_match_index(0);
    }
    request.mutable_variable()->set_bind("v");
    request.mutable_function()->set_bind("f");
  }
  ctk::clang_layer::CfgResult run() {
    events.clear();
    return cfg.variable_flow(
        request, [] { return true; },
        [&](const auto &event, std::string &) {
          events.push_back(event);
          return MatchCode::Ok;
        },
        "owner");
  }
  std::vector<pb::VariableFlowFact> facts() {
    std::vector<pb::VariableFlowFact> result;
    for (const auto &event : events)
      if (event.has_fact())
        result.push_back(event.fact());
    return result;
  }
  pb::VariableFlowFact at(unsigned line, pb::VariableUsage::Kind kind) {
    for (const auto &event : events)
      if (event.has_usage() && event.usage().location().line() == line &&
          event.usage().kind() == kind)
        for (const auto &fact : facts())
          if (fact.usage_id() == event.usage().id())
            return fact;
    ADD_FAILURE() << "missing usage on line " << line;
    return {};
  }
  void interval(const pb::VariableValueRange &value, const char *lower,
                const char *upper) {
    EXPECT_EQ(value.kind(), pb::VariableValueRange::INTERVAL);
    EXPECT_EQ(value.lower(), lower);
    EXPECT_EQ(value.upper(), upper);
  }
};
TEST_F(VariableFlow, BranchJoinAndOverwriteUseRetainedDeclarations) {
  select("void use(int);\nvoid example(bool ready) {\nint x;\nif(ready) "
         "x=10;\nuse(x);\nx=20;\nx=30;\nuse(x);\n}\n");
  std::filesystem::remove(directory.path() / "flow.cc");
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_TRUE(events.back().completed().is_complete());
  int reads = 0, dead = 0, uninit = 0;
  std::uint64_t conditional_write = 0, final_write = 0;
  for (const auto &event : events)
    if (event.has_usage()) {
      const auto &usage = event.usage();
      if (usage.location().line() == 4)
        conditional_write = usage.id();
      if (usage.location().line() == 7)
        final_write = usage.id();
    }
  for (const auto &event : events) {
    if (event.has_finding()) {
      if (event.finding().kind() ==
          pb::VariableFlowFinding::POSSIBLY_UNINITIALIZED) {
        ++uninit;
        EXPECT_GT(event.finding().witness_blocks_size(), 1);
      }
      dead += event.finding().kind() == pb::VariableFlowFinding::DEAD_STORE;
    }
    if (event.has_fact() && event.fact().reaching_assignments_size()) {
      ++reads;
      if (event.fact().initialization() ==
          pb::VariableFlowFact::MAYBE_INITIALIZED) {
        EXPECT_EQ(event.fact().reaching_assignments_size(), 2);
        EXPECT_EQ(event.fact().reaching_assignments(0), 0);
        EXPECT_EQ(event.fact().reaching_assignments(1), conditional_write);
      } else
        EXPECT_EQ(event.fact().reaching_assignments(0), final_write);
    }
  }
  EXPECT_EQ(reads, 2);
  EXPECT_EQ(dead, 1);
  EXPECT_EQ(uninit, 1);
}
TEST_F(VariableFlow, LoopAndShortCircuitConvergeInExecutionOrder) {
  select("void use(int); void example(bool ready) { int x; while(ready) { x=1; "
         "use(x); } ready && (x=2); use(x); }");
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_TRUE(events.back().completed().is_complete());
  bool maybe = false, initialized = false;
  for (const auto &fact : facts())
    if (fact.reaching_assignments_size()) {
      maybe |= fact.initialization() == pb::VariableFlowFact::MAYBE_INITIALIZED;
      initialized |= fact.initialization() == pb::VariableFlowFact::INITIALIZED;
    }
  EXPECT_TRUE(maybe);
  EXPECT_TRUE(initialized);
}
TEST_F(VariableFlow, ShadowedNamesAndReadModifyWriteRemainDistinct) {
  select("void use(int); void example() { int x=1; { int x=9; use(x); } x+=1; "
         "++x; use(x); }");
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  int usages = 0, read_writes = 0;
  for (const auto &event : events)
    if (event.has_usage()) {
      ++usages;
      read_writes += event.usage().kind() == pb::VariableUsage::READ_WRITE;
    }
  EXPECT_EQ(usages, 4);
  EXPECT_EQ(read_writes, 2);
  EXPECT_EQ(events.back().completed().finding_count(), 0);
  auto outer_id = events.front().started().declaration_id();
  request.mutable_variable()->set_match_index(1);
  request.mutable_function()->set_match_index(1);
  result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_NE(events.front().started().declaration_id(), outer_id);
  EXPECT_EQ(events.back().completed().usage_count(), 2);
  EXPECT_EQ(events.back().completed().finding_count(), 0);
}
TEST_F(VariableFlow, EscapesAndUnsupportedTypesCannotProduceCleanFindings) {
  for (auto body :
       {"void touch(int*); void example() { int x=1; touch(&x); x=2; }",
        "void touch(int&); void example() { int x=1; touch(x); x=2; }",
        "void example() { volatile int x=1; x=2; }",
        "void example() { int x=1; auto f=[&x]{return x;}; x=2; }"}) {
    select(body);
    auto result = run();
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    EXPECT_FALSE(events.back().completed().is_complete());
    for (const auto &fact : facts()) {
      EXPECT_EQ(fact.initialization(), pb::VariableFlowFact::UNKNOWN);
      EXPECT_FALSE(fact.dead_store());
    }
  }
}
TEST_F(VariableFlow,
       LimitsCancellationAndRevisionFailureNeverPublishCompletion) {
  select("void use(int); void example(bool b) { int x; if(b) x=1; use(x); }");
  request.set_max_events(1);
  EXPECT_EQ(run().code, MatchCode::ResourceExhausted);
  EXPECT_FALSE(events.back().has_completed());
  request.clear_max_events();
  request.set_max_events(8);
  EXPECT_EQ(run().code, MatchCode::ResourceExhausted);
  EXPECT_EQ(events.size(), 8);
  EXPECT_FALSE(events.back().has_completed());
  request.clear_max_events();
  request.set_max_iterations(1);
  EXPECT_EQ(run().code, MatchCode::ResourceExhausted);
  EXPECT_FALSE(events.back().has_completed());
  request.clear_max_iterations();
  int writes = 0;
  auto result = cfg.variable_flow(
      request, [] { return true; },
      [&](const auto &, std::string &) {
        ++writes;
        return MatchCode::Cancelled;
      },
      "owner");
  EXPECT_EQ(result.code, MatchCode::Cancelled);
  EXPECT_EQ(writes, 1);
  request.mutable_variable()->set_expected_result_revision(99999);
  EXPECT_EQ(run().code, MatchCode::Aborted);
  EXPECT_TRUE(events.empty());
}
TEST_F(VariableFlow, AssignmentAndPrefixResultsReadTheNewValue) {
  select("void use(int); void example() { int x; int y=(x=5); use(y); "
         "use(++x); }");
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_TRUE(events.back().completed().is_complete());
  for (const auto &fact : facts())
    EXPECT_FALSE(fact.dead_store());
  EXPECT_EQ(events.back().completed().finding_count(), 0);
}
TEST_F(VariableFlow, ReadModifyWriteCanBeBothUninitializedAndDead) {
  select("void example() { int x; ++x; }");
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_EQ(events.back().completed().finding_count(), 2);
}
TEST_F(VariableFlow, OlderCppAssignmentResultsDoNotBecomeFalseDeadStores) {
  select("void use(int); void example() { int x; int y=(x=5); use(y); }",
         "c++14");
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_TRUE(events.back().completed().is_complete());
  for (const auto &fact : facts())
    EXPECT_FALSE(fact.dead_store());
}
TEST_F(VariableFlow, RejectsCrossSnapshotAndAmbiguousSelections) {
  select("void example(){int x=1;} void other(){int z=2;}");
  auto old_function = request.function();
  select("void example(){int x=2; { int x=3; }}");
  request.mutable_variable()->clear_match_index();
  EXPECT_EQ(run().code, MatchCode::InvalidArgument);
  EXPECT_TRUE(events.empty());
  request.mutable_variable()->set_match_index(0);
  request.mutable_function()->CopyFrom(old_function);
  EXPECT_EQ(run().code, MatchCode::InvalidArgument);
  EXPECT_TRUE(events.empty());
}
TEST_F(VariableFlow, UnsequencedOlderCppAssignmentsRemainUnknown) {
  for (auto statement : {"x=x++ + 1;", "x+=x++;"}) {
    select(std::string("void example(){int x=1;") + statement + "}", "c++14");
    auto result = run();
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    EXPECT_FALSE(events.back().completed().is_complete());
  }
}
TEST_F(VariableFlow, SmallEventsAndForeignOwnerFailWithoutCompletion) {
  select("void example(){int x=1;}");
  CursorSettings settings;
  settings.results.max_bytes = 16;
  CfgController limited(settings, {}, {}, &matches);
  auto result = limited.variable_flow(
      request, [] { return true; },
      [&](const auto &event, std::string &) {
        events.push_back(event);
        return MatchCode::Ok;
      },
      "owner");
  EXPECT_EQ(result.code, MatchCode::ResourceExhausted);
  EXPECT_TRUE(events.empty());
  result = cfg.variable_flow(
      request, [] { return true; },
      [&](const auto &event, std::string &) {
        events.push_back(event);
        return MatchCode::Ok;
      },
      "foreign");
  EXPECT_NE(result.code, MatchCode::Ok);
  EXPECT_TRUE(events.empty());
}
TEST_F(VariableFlow, NonLocalJumpsAndIndirectCallsRemainUnknown) {
  for (auto body :
       {"int setjmp(void*) __attribute__((returns_twice)); void example() { "
        "int x=1; if(setjmp(nullptr)) x=2; }",
        "void example(void(*callback)(int)) { int x=1; callback(x); }"}) {
    select(body);
    auto result = run();
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    EXPECT_FALSE(events.back().completed().is_complete());
  }
}
TEST_F(VariableFlow, CatchParameterInitializationIsExplicitlyUnsupported) {
  select("void may_throw(); void use(int); void example(){try { may_throw(); } "
         "catch(int x) { use(x); }}");
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_FALSE(events.back().completed().is_complete());
  for (const auto &fact : facts())
    EXPECT_EQ(fact.initialization(), pb::VariableFlowFact::UNKNOWN);
}
TEST_F(VariableFlow, ReturningTheSelectedLocalReadsItsValue) {
  for (auto standard : {"c++20", "c++23"}) {
    select("int example(){int x=1; return x;}", standard);
    auto result = run();
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    for (const auto &event : events)
      if (event.has_finding())
        ADD_FAILURE() << event.finding().DebugString();
    EXPECT_TRUE(events.back().completed().is_complete());
    EXPECT_EQ(events.back().completed().usage_count(), 2);
  }
}
TEST_F(VariableFlow, ReferencesToAssignmentAndIncrementResultsRemainUnknown) {
  for (auto body :
       {"void use(int); void example(){int x=0; int &r=(x=1); r=2; use(x);}",
        "void touch(int&); void example(){int x=0; touch(++x);}"}) {
    select(body);
    auto result = run();
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    EXPECT_FALSE(events.back().completed().is_complete());
    for (const auto &fact : facts())
      EXPECT_EQ(fact.initialization(), pb::VariableFlowFact::UNKNOWN);
  }
}
TEST_F(VariableFlow, UnbracedBranchAndLoopWritesRemainSupported) {
  select("void use(int); void example(bool ready){int x=0; if(ready) x=1; else "
         "x=2; while(ready) ++x; do x+=1; while(ready); switch(x) { case 0: "
         "x=3; break; default: x=4; } use(x);}");
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_TRUE(events.back().completed().is_complete());
}
TEST_F(VariableFlow, IntervalPageLoopRecoversCapInvariantAfterConvergence) {
  select(
      "int example(int rounds) {\nint x = 0;\n"
      "for(int i=0;i<rounds;++i) {\nif(i%2==0) {\nx+=2;\n} else {\nx+=1;\n}\n"
      "if(x>10) {\nx=10;\n}\n}\nreturn x;\n}\n");
  request.set_value_domain(pb::INTERVAL);
  std::filesystem::remove(directory.path() / "flow.cc");
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_EQ(events.front().started().value_domain(), pb::INTERVAL);
  ASSERT_TRUE(events.back().completed().is_complete());
  EXPECT_EQ(events.back().completed().finding_count(), 0);
  auto init = at(2, pb::VariableUsage::INITIALIZE);
  EXPECT_EQ(init.value_before().kind(), pb::VariableValueRange::UNINITIALIZED);
  interval(init.value_after(), "0", "0");
  auto even = at(5, pb::VariableUsage::READ_WRITE);
  interval(even.value_before(), "0", "10");
  interval(even.value_after(), "2", "12");
  auto odd = at(7, pb::VariableUsage::READ_WRITE);
  interval(odd.value_before(), "0", "10");
  interval(odd.value_after(), "1", "11");
  interval(at(9, pb::VariableUsage::READ).value_before(), "1", "12");
  auto cap = at(10, pb::VariableUsage::WRITE);
  interval(cap.value_before(), "11", "12");
  interval(cap.value_after(), "10", "10");
  interval(at(13, pb::VariableUsage::READ).value_before(), "0", "10");
}
TEST_F(VariableFlow, NumericBoundsAreAbsentUnlessRequested) {
  select("int example(){int x=1;return x;}");
  ASSERT_EQ(run().code, MatchCode::Ok);
  EXPECT_EQ(events.front().started().value_domain(),
            pb::VARIABLE_VALUE_DOMAIN_UNSPECIFIED);
  for (const auto &fact : facts()) {
    EXPECT_FALSE(fact.has_value_before());
    EXPECT_FALSE(fact.has_value_after());
  }
  request.set_value_domain(static_cast<pb::VariableValueDomain>(99));
  EXPECT_EQ(run().code, MatchCode::InvalidArgument);
}
TEST_F(VariableFlow, NumericUnknownInputsRefineAtBothBranchEdges) {
  select("int example(int n){\nint x=n;\nif(x<0)x=0;\nif(x>10)x=10;\nreturn "
         "x;\n}");
  request.set_value_domain(pb::INTERVAL);
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_TRUE(events.back().completed().is_complete());
  interval(at(5, pb::VariableUsage::READ).value_before(), "0", "10");
}
TEST_F(VariableFlow, NumericReversedGuardPrunesImpossibleWrite) {
  select("int example(){\nint x=5;\nif(10<x) {\nx=99;\n}\nreturn x;\n}");
  request.set_value_domain(pb::INTERVAL);
  ASSERT_EQ(run().code, MatchCode::Ok);
  EXPECT_TRUE(events.back().completed().is_complete());
  EXPECT_EQ(at(4, pb::VariableUsage::WRITE).value_before().kind(),
            pb::VariableValueRange::UNREACHABLE);
  interval(at(6, pb::VariableUsage::READ).value_before(), "5", "5");
}
TEST_F(VariableFlow, NumericLoopDecrementAndZeroExitAreStable) {
  select("int example(){\nint x=10;\nwhile(x>0){\n--x;\n}\nreturn x;\n}");
  request.set_value_domain(pb::INTERVAL);
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_TRUE(events.back().completed().is_complete());
  interval(at(4, pb::VariableUsage::READ_WRITE).value_before(), "1", "10");
  interval(at(4, pb::VariableUsage::READ_WRITE).value_after(), "0", "9");
  interval(at(6, pb::VariableUsage::READ).value_before(), "0", "0");
}
TEST_F(VariableFlow, NumericRangesPreserveUninitializedPossibilitySeparately) {
  select("void use(int); void example(bool c){\nint x;\nif(c)x=3;\nuse(x);\n}");
  request.set_value_domain(pb::INTERVAL);
  ASSERT_EQ(run().code, MatchCode::Ok);
  auto read = at(4, pb::VariableUsage::READ);
  EXPECT_EQ(read.initialization(), pb::VariableFlowFact::MAYBE_INITIALIZED);
  interval(read.value_before(), "3", "3");
  EXPECT_TRUE(events.back().completed().is_complete());
  bool warning = false;
  for (const auto &event : events)
    warning |= event.has_finding() &&
               event.finding().kind() ==
                   pb::VariableFlowFinding::POSSIBLY_UNINITIALIZED;
  EXPECT_TRUE(warning);
}
TEST_F(VariableFlow, NumericOverflowAndUnsupportedEffectsCannotPublishBounds) {
  for (auto source :
       {"int example(){int x=__INT_MAX__; ++x; return x;}",
        "void use(int); void example(){int x=__INT_MAX__; use(x+1);}",
        "int example(){int x=1; x*=2; return x;}",
        "int example(){int x=1; x=(x=5)+1; return x;}",
        "int example(){signed char x=127; ++x; return x;}",
        "unsigned example(){unsigned x=1; return x;}"}) {
    SCOPED_TRACE(source);
    select(source);
    request.set_value_domain(pb::INTERVAL);
    auto result = run();
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    EXPECT_FALSE(events.back().completed().is_complete());
    bool numeric_issue = false;
    for (const auto &event : events)
      numeric_issue |= event.has_finding() &&
                       (event.finding().kind() ==
                            pb::VariableFlowFinding::POSSIBLE_OVERFLOW ||
                        event.finding().kind() ==
                            pb::VariableFlowFinding::UNSUPPORTED_EFFECT);
    EXPECT_TRUE(numeric_issue);
    for (const auto &fact : facts()) {
      EXPECT_EQ(fact.value_before().kind(), pb::VariableValueRange::UNKNOWN);
      EXPECT_EQ(fact.value_after().kind(), pb::VariableValueRange::UNKNOWN);
    }
  }
}
TEST_F(VariableFlow, NumericBoundsPreserveIntegersBeyondJsonDoublePrecision) {
  select("__int128 example(){\n__int128 "
         "x=18446744073709551615ULL;\nx+=1;\nreturn x;\n}");
  request.set_value_domain(pb::INTERVAL);
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_TRUE(events.back().completed().is_complete());
  interval(at(4, pb::VariableUsage::READ).value_before(),
           "18446744073709551616", "18446744073709551616");
}
TEST_F(VariableFlow,
       NumericNegatedTruthGuardRefinesZeroAndMergesDuplicateEdges) {
  select("int example(int n){\nint x=n;\nif(!x){\nx=5;\n}\nif(x>0){}\nreturn "
         "x;\n}");
  request.set_value_domain(pb::INTERVAL);
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_TRUE(events.back().completed().is_complete());
  interval(at(4, pb::VariableUsage::WRITE).value_before(), "0", "0");
  interval(at(7, pb::VariableUsage::READ).value_before(), "-2147483648",
           "2147483647");
}
TEST_F(VariableFlow, NumericForAndDoConditionsRefineTheCorrectSuccessors) {
  for (auto body :
       {"int example(){\nint x=0;\nfor(;x<3;){++x;}\nreturn x;\n}",
        "int example(){\nint x=3;\ndo{--x;}while(x>0);\nreturn x;\n}"}) {
    SCOPED_TRACE(body);
    select(body);
    request.set_value_domain(pb::INTERVAL);
    auto result = run();
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    ASSERT_TRUE(events.back().completed().is_complete());
    const char *expected =
        std::string(body).find("for(") != std::string::npos ? "3" : "0";
    interval(at(4, pb::VariableUsage::READ).value_before(), expected, expected);
  }
}
TEST_F(VariableFlow, NumericLogicalAndRefinesBothConditionsBeforeTheWrite) {
  select(
      "int example(int n){\nint x=n;\nif(x>2 && x<5){\nx+=1;\n}\nreturn x;\n}");
  request.set_value_domain(pb::INTERVAL);
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_TRUE(events.back().completed().is_complete());
  interval(at(4, pb::VariableUsage::READ_WRITE).value_before(), "3", "4");
  interval(at(4, pb::VariableUsage::READ_WRITE).value_after(), "4", "5");
}
TEST_F(VariableFlow, NumericLogicalOrRejectsBothFalseAlternatives) {
  select("int example(){\nint x=3;\nif(x<2 || "
         "x>4){\nx=6;\n}else{\nx=7;\n}\nreturn x;\n}");
  request.set_value_domain(pb::INTERVAL);
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_TRUE(events.back().completed().is_complete());
  EXPECT_EQ(at(4, pb::VariableUsage::WRITE).value_before().kind(),
            pb::VariableValueRange::UNREACHABLE);
  interval(at(8, pb::VariableUsage::READ).value_before(), "7", "7");
}
TEST_F(VariableFlow, NumericConditionalExpressionRefinesItsGuardedRead) {
  select("int example(int n){\nint x=n;\nint y = x<0 ?\nx :\n0;\nreturn x;\n}");
  request.set_value_domain(pb::INTERVAL);
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_TRUE(events.back().completed().is_complete());
  interval(at(4, pb::VariableUsage::READ).value_before(), "-2147483648", "-1");
  interval(at(6, pb::VariableUsage::READ).value_before(), "-2147483648",
           "2147483647");
}
TEST_F(VariableFlow, NumericConversionsRespectPromotionsAndRejectLostValues) {
  for (auto body :
       {"int example(){\nshort x=-7;\nx=(long long)x+2;\nreturn x;\n}",
        "int example(){\nint x=12;\nx=(signed char)x;\nreturn x;\n}",
        "int example(){\nint x=-7;\nx=bool(x);\nreturn x;\n}"}) {
    SCOPED_TRACE(body);
    select(body);
    request.set_value_domain(pb::INTERVAL);
    auto result = run();
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    ASSERT_TRUE(events.back().completed().is_complete());
    std::string source = body;
    const char *expected = source.find("short x") != std::string::npos   ? "-5"
                           : source.find("bool(x)") != std::string::npos ? "1"
                                                                         : "12";
    interval(at(4, pb::VariableUsage::READ).value_before(), expected, expected);
  }
  for (auto body : {"int example(){int x=128; x=(signed char)x; return x;}",
                    "int example(){int x=-1; x=(unsigned)x; return x;}",
                    "int example(){int x=-1; x+=1u; return x;}"}) {
    SCOPED_TRACE(body);
    select(body);
    request.set_value_domain(pb::INTERVAL);
    ASSERT_EQ(run().code, MatchCode::Ok);
    EXPECT_FALSE(events.back().completed().is_complete());
    for (const auto &fact : facts())
      EXPECT_EQ(fact.value_after().kind(), pb::VariableValueRange::UNKNOWN);
  }
}
TEST_F(VariableFlow, NumericUnboundedGrowthWidensAndReportsOverflow) {
  select("void example(bool c){int x=0;while(c){++x;}}");
  request.set_value_domain(pb::INTERVAL);
  request.set_max_iterations(10000);
  auto result = run();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_FALSE(events.back().completed().is_complete());
  bool overflow = false;
  for (const auto &event : events)
    overflow |=
        event.has_finding() &&
        event.finding().kind() == pb::VariableFlowFinding::POSSIBLE_OVERFLOW;
  EXPECT_TRUE(overflow);
}
TEST_F(VariableFlow, NumericUnsupportedInputTypesCannotEraseReachableRoutes) {
  // x86 supports integers wider than 128 bits in newer Clang releases. Older
  // releases still exercise an unsupported unknown-input narrowing conversion.
  const std::string prefix =
      "#if defined(__BITINT_MAXWIDTH__) && __BITINT_MAXWIDTH__ >= 256\n"
      "using Wide = _BitInt(256);\n#else\n"
      "using Wide = unsigned long long;\n#endif\n";
  for (auto source :
       {"int example(Wide n){int x=(int)n;return x;}",
        "Wide input(); int example(){int x=(int)input();return x;}"}) {
    SCOPED_TRACE(source);
    ASSERT_NO_FATAL_FAILURE(
        select(prefix + source, "c++20", "x86_64-linux-gnu"));
    request.set_value_domain(pb::INTERVAL);
    auto result = run();
    ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
    EXPECT_FALSE(events.back().completed().is_complete());
    EXPECT_GT(events.back().completed().finding_count(), 0);
    for (const auto &fact : facts()) {
      EXPECT_EQ(fact.value_before().kind(), pb::VariableValueRange::UNKNOWN);
      EXPECT_EQ(fact.value_after().kind(), pb::VariableValueRange::UNKNOWN);
    }
  }
}
} // namespace
} // namespace ctk::application
