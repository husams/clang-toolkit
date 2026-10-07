#include "ctk/application/match_controller.hpp"
#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <future>
#include <gtest/gtest.h>
#include <thread>

namespace ctk::application {
namespace {
using ctk::clang_layer::MatchCode;
using namespace ctk::match::v1;
class MatchCursors : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory directory{"ctk-match-cursors"};
  std::unique_ptr<MatchController> controller;
  void SetUp() override { reset(); }
  void reset(CursorSettings settings = {}) {
    controller = std::make_unique<MatchController>(settings);
    std::ofstream(directory.path() / "fixture.cc")
        << "int callee(int x) { return x; }\n"
           "int alpha() { int value=7; callee(value); return callee(3); }\n"
           "int beta() { return callee(2); }\n";
  }
  MatchRequest file(std::string query) {
    MatchRequest request;
    request.set_query(query);
    request.mutable_file()->set_file_path("fixture.cc");
    request.mutable_file()->set_working_directory(directory.path().string());
    request.mutable_file()->add_compile_arguments("-std=c++20");
    return request;
  }
  ParseRequest parse_request() {
    ParseRequest request;
    const auto target = file("unused").file();
    request.set_file_path(target.file_path());
    request.set_working_directory(target.working_directory());
    request.mutable_compile_arguments()->CopyFrom(target.compile_arguments());
    return request;
  }
  MatchResponse tree_response(const ParseResponse &tree) {
    MatchResponse response;
    response.set_session_id(tree.session_id());
    response.set_result_revision(tree.result_revision());
    response.mutable_expires_at()->CopyFrom(tree.expires_at());
    return response;
  }
  MatchReply fork(MatchRequest request, std::string owner = "owner") {
    request.set_preserve_source(true);
    return run(request, std::move(owner));
  }
  MatchRequest session(const MatchResponse &old, std::string query,
                       bool guard = true) {
    MatchRequest request;
    request.set_query(query);
    request.mutable_session()->set_session_id(old.session_id());
    if (guard)
      request.mutable_session()->set_expected_result_revision(
          old.result_revision());
    return request;
  }
  MatchRequest binding(const MatchResponse &old, std::string bind,
                       std::string query) {
    MatchRequest request;
    request.set_query(query);
    request.mutable_binding()->set_session_id(old.session_id());
    request.mutable_binding()->set_bind(bind);
    request.mutable_binding()->set_expected_result_revision(
        old.result_revision());
    return request;
  }
  MatchReply run(const MatchRequest &request, std::string owner = "owner") {
    return controller->match(owner, request, [] { return true; });
  }
};

TEST_F(MatchCursors, ParsePinsTreeWithoutRowsAndAllowsIndependentReuse) {
  const auto parsed =
      controller->parse("owner", parse_request(), [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  EXPECT_EQ(parsed.response.result_revision(), 1U);
  EXPECT_TRUE(parsed.response.has_expires_at());
  const auto tree = tree_response(parsed.response);
  EXPECT_EQ(run(binding(tree, "root", "callExpr()")).code, MatchCode::NotFound);
  const auto calls = fork(session(tree, "callExpr().bind(\"call\")"));
  const auto functions = fork(session(tree, "functionDecl().bind(\"fn\")"));
  ASSERT_EQ(calls.code, MatchCode::Ok) << calls.message;
  ASSERT_EQ(functions.code, MatchCode::Ok) << functions.message;
  EXPECT_EQ(calls.response.results_size(), 3);
  EXPECT_EQ(functions.response.results_size(), 3);
  EXPECT_EQ(calls.response.result_revision(), 1U);
  EXPECT_EQ(functions.response.result_revision(), 1U);
  EXPECT_NE(calls.response.session_id(), tree.session_id());
  EXPECT_NE(functions.response.session_id(), calls.response.session_id());
  EXPECT_EQ(controller->close("owner", tree.session_id()).code, MatchCode::Ok);
  EXPECT_EQ(run(session(calls.response, "callExpr()")).code, MatchCode::Ok);
  EXPECT_EQ(run(session(functions.response, "functionDecl()")).code,
            MatchCode::Ok);
}

TEST_F(MatchCursors, ForkedContinuationsPreserveSourceRowsAndRevision) {
  const auto source =
      run(file("functionDecl(hasName(\"alpha\")).bind(\"function\")"));
  ASSERT_EQ(source.code, MatchCode::Ok) << source.message;
  const auto first =
      fork(binding(source.response, "function", "callExpr().bind(\"call\")"));
  const auto second = fork(
      binding(source.response, "function", "integerLiteral().bind(\"n\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  ASSERT_EQ(second.code, MatchCode::Ok) << second.message;
  EXPECT_EQ(first.response.results_size(), 2);
  EXPECT_EQ(second.response.results_size(), 2);
  EXPECT_EQ(first.response.result_revision(), 1U);
  EXPECT_NE(first.response.session_id(), source.response.session_id());
  EXPECT_NE(second.response.session_id(), first.response.session_id());
  for (const auto &row : first.response.results())
    EXPECT_EQ(row.source_match_index(), 0U);
  EXPECT_EQ(controller->close("owner", first.response.session_id()).code,
            MatchCode::Ok);
  const auto original =
      run(binding(source.response, "function", "callExpr().bind(\"call\")"));
  ASSERT_EQ(original.code, MatchCode::Ok) << original.message;
  EXPECT_EQ(original.response.result_revision(), 2U);
  EXPECT_EQ(original.response.results_size(), 2);
  EXPECT_EQ(run(session(second.response, "integerLiteral()")).code,
            MatchCode::Ok);
}

TEST_F(MatchCursors, PreservedEmptyCollectionsSelectZeroRootsWithoutIndex) {
  const auto source = run(file("functionDecl(hasName(\"missing\"))"));
  ASSERT_EQ(source.code, MatchCode::Ok) << source.message;
  auto select = binding(source.response, "function", "callExpr()");
  EXPECT_EQ(run(select).code, MatchCode::NotFound);
  const auto empty = fork(select);
  ASSERT_EQ(empty.code, MatchCode::Ok) << empty.message;
  EXPECT_EQ(empty.response.results_size(), 0);
  EXPECT_NE(empty.response.session_id(), source.response.session_id());
  EXPECT_EQ(empty.response.result_revision(), 1U);
  select.mutable_binding()->set_match_index(0);
  EXPECT_EQ(fork(select).code, MatchCode::NotFound);
  auto invalid = binding(source.response, "function", "invalidMatcher()");
  EXPECT_EQ(fork(invalid).code, MatchCode::InvalidArgument);
  const auto nonempty = run(file("functionDecl()"));
  ASSERT_EQ(nonempty.code, MatchCode::Ok) << nonempty.message;
  EXPECT_EQ(fork(binding(nonempty.response, "function", "callExpr()")).code,
            MatchCode::NotFound);
  EXPECT_EQ(fork(binding(empty.response, "function", "callExpr()")).code,
            MatchCode::Ok);
}

TEST_F(MatchCursors, ForksKeepOverlapMultiplicityAndExactRowSelection) {
  const auto source =
      run(file("functionDecl(hasName(\"alpha\"), "
               "forEachDescendant(callExpr().bind(\"c\"))).bind(\"f\")"));
  ASSERT_EQ(source.code, MatchCode::Ok) << source.message;
  auto selected = binding(source.response, "f", "callExpr()");
  const auto all = fork(selected);
  ASSERT_EQ(all.code, MatchCode::Ok) << all.message;
  ASSERT_EQ(all.response.results_size(), 4);
  EXPECT_EQ(all.response.results(0).source_match_index(), 0U);
  EXPECT_EQ(all.response.results(2).source_match_index(), 1U);
  selected.mutable_binding()->set_match_index(0);
  const auto exact = fork(selected);
  ASSERT_EQ(exact.code, MatchCode::Ok) << exact.message;
  EXPECT_EQ(exact.response.results_size(), 2);
  selected.mutable_binding()->set_match_index(9);
  EXPECT_EQ(fork(selected).code, MatchCode::NotFound);
}

TEST_F(MatchCursors, ParseAndForkKeepPinnedGenerationAfterSourceChange) {
  const auto parsed =
      controller->parse("owner", parse_request(), [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  const auto tree = tree_response(parsed.response);
  std::ofstream(directory.path() / "fixture.cc") << "int changed=99;";
  const auto fresh = run(file("integerLiteral().bind(\"n\")"));
  ASSERT_EQ(fresh.code, MatchCode::Ok) << fresh.message;
  EXPECT_EQ(fresh.response.results_size(), 1);
  const auto old = fork(session(tree, "integerLiteral().bind(\"n\")"));
  ASSERT_EQ(old.code, MatchCode::Ok) << old.message;
  EXPECT_EQ(old.response.results_size(), 3);
  EXPECT_EQ(controller->close("owner", tree.session_id()).code, MatchCode::Ok);
  const auto still_pinned = run(session(old.response, "integerLiteral()"));
  ASSERT_EQ(still_pinned.code, MatchCode::Ok) << still_pinned.message;
  EXPECT_EQ(still_pinned.response.results_size(), 3);
}

TEST_F(MatchCursors, ForkFailuresPreserveSourceAndEnforceCallerOwnership) {
  const auto source = run(file("functionDecl(hasName(\"alpha\")).bind(\"f\")"));
  ASSERT_EQ(source.code, MatchCode::Ok) << source.message;
  EXPECT_EQ(fork(session(source.response, "invalidMatcher()")).code,
            MatchCode::InvalidArgument);
  auto stale = session(source.response, "callExpr()");
  stale.mutable_session()->set_expected_result_revision(9);
  EXPECT_EQ(fork(stale).code, MatchCode::Aborted);
  EXPECT_EQ(fork(session(source.response, "callExpr()"), "other").code,
            MatchCode::NotFound);
  auto cancelled = binding(source.response, "f", "callExpr()");
  cancelled.set_preserve_source(true);
  EXPECT_EQ(controller->match("owner", cancelled, [] { return false; }).code,
            MatchCode::Cancelled);
  const auto valid = fork(binding(source.response, "f", "callExpr()"));
  ASSERT_EQ(valid.code, MatchCode::Ok) << valid.message;
  EXPECT_EQ(fork(session(valid.response, "callExpr()"), "other").code,
            MatchCode::NotFound);
  EXPECT_EQ(controller->close("other", source.response.session_id()).code,
            MatchCode::Ok);
  EXPECT_EQ(fork(binding(source.response, "f", "callExpr()")).code,
            MatchCode::Ok);
}

TEST_F(MatchCursors, ForkResultLimitsLeaveSourceSelectable) {
  CursorSettings settings;
  settings.results.max_rows = 1;
  reset(settings);
  const auto source = run(file("functionDecl(hasName(\"alpha\")).bind(\"f\")"));
  ASSERT_EQ(source.code, MatchCode::Ok) << source.message;
  EXPECT_EQ(fork(binding(source.response, "f", "callExpr()")).code,
            MatchCode::ResourceExhausted);
  auto root = binding(source.response, "f", "functionDecl()");
  root.mutable_binding()->set_scope(BINDING_MATCH_SCOPE_ROOT_ONLY);
  EXPECT_EQ(fork(root).code, MatchCode::Ok);
  EXPECT_EQ(fork(root).code, MatchCode::Ok);
}

TEST_F(MatchCursors, ConcurrentForksAcceptSameSourceRevisionIndependently) {
  const auto source = run(file("callExpr()"));
  ASSERT_EQ(source.code, MatchCode::Ok) << source.message;
  auto task = [&] {
    return fork(session(source.response, "integerLiteral()"));
  };
  auto a = std::async(std::launch::async, task);
  auto b = std::async(std::launch::async, task);
  const auto left = a.get();
  const auto right = b.get();
  ASSERT_EQ(left.code, MatchCode::Ok) << left.message;
  ASSERT_EQ(right.code, MatchCode::Ok) << right.message;
  EXPECT_NE(left.response.session_id(), right.response.session_id());
  EXPECT_EQ(left.response.result_revision(), 1U);
  EXPECT_EQ(right.response.result_revision(), 1U);
  EXPECT_EQ(fork(session(source.response, "callExpr()")).code, MatchCode::Ok);
}

TEST_F(MatchCursors, ForkAndParseCountLimitsPublishNothingOnFailure) {
  CursorSettings settings;
  settings.max_cursors = 1;
  reset(settings);
  const auto parsed =
      controller->parse("owner", parse_request(), [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  const auto tree = tree_response(parsed.response);
  EXPECT_EQ(fork(session(tree, "callExpr()")).code,
            MatchCode::ResourceExhausted);
  EXPECT_EQ(
      controller->parse("owner", parse_request(), [] { return true; }).code,
      MatchCode::ResourceExhausted);
  const auto legacy = run(session(tree, "callExpr()"));
  ASSERT_EQ(legacy.code, MatchCode::Ok) << legacy.message;
  EXPECT_EQ(legacy.response.result_revision(), 2U);
  EXPECT_EQ(controller->close("owner", tree.session_id()).code, MatchCode::Ok);
  EXPECT_EQ(
      controller->parse("owner", parse_request(), [] { return true; }).code,
      MatchCode::Ok);
}

TEST_F(MatchCursors, ForkDoesNotRenewSourceExpiry) {
  CursorSettings settings;
  settings.idle_ttl = std::chrono::milliseconds(200);
  reset(settings);
  const auto parsed =
      controller->parse("owner", parse_request(), [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  const auto tree = tree_response(parsed.response);
  std::this_thread::sleep_for(std::chrono::milliseconds(120));
  const auto derived = fork(session(tree, "callExpr()"));
  ASSERT_EQ(derived.code, MatchCode::Ok) << derived.message;
  std::this_thread::sleep_for(std::chrono::milliseconds(120));
  EXPECT_EQ(fork(session(tree, "callExpr()")).code, MatchCode::NotFound);
  EXPECT_EQ(run(session(derived.response, "callExpr()")).code, MatchCode::Ok);
}

TEST_F(MatchCursors, ParseRejectsInvalidFilesFlagsCancellationAndMemoryLimits) {
  auto request = parse_request();
  EXPECT_EQ(controller->parse("", request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  request.set_working_directory("relative");
  EXPECT_EQ(controller->parse("owner", request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  request = parse_request();
  request.add_compile_arguments("-std=c17");
  EXPECT_EQ(controller->parse("owner", request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  request = parse_request();
  request.set_file_path("missing.cc");
  EXPECT_EQ(controller->parse("owner", request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  EXPECT_EQ(
      controller->parse("owner", parse_request(), [] { return false; }).code,
      MatchCode::Cancelled);
  std::ofstream(directory.path() / "fixture.cc") << "int invalid = ;";
  EXPECT_EQ(
      controller->parse("owner", parse_request(), [] { return true; }).code,
      MatchCode::InvalidArgument);
  CursorSettings settings;
  settings.max_memory_bytes = 1;
  reset(settings);
  const auto limited =
      controller->parse("owner", parse_request(), [] { return true; });
  EXPECT_EQ(limited.code, MatchCode::ResourceExhausted);
  EXPECT_TRUE(limited.response.session_id().empty());
}

class AcquisitionOnlyEngine final : public ctk::clang_layer::IQueryEngine {
public:
  std::size_t acquisitions{}, matches{};
  ctk::clang_layer::QueryResult match(const ctk::clang_layer::FileInput &,
                                      const std::string &, const Checkpoint &,
                                      const MatchCallback &) override {
    ++matches;
    return {};
  }
  ctk::cache::SnapshotPtr
  acquire_snapshot(const ctk::clang_layer::FileInput &file) override {
    ++acquisitions;
    return native_->acquire_snapshot(file);
  }

private:
  std::shared_ptr<ctk::clang_layer::IQueryEngine> native_ =
      ctk::clang_layer::make_query_engine();
};

TEST_F(MatchCursors, NativeParseReusesSnapshotAndNeverEvaluatesMatcher) {
  auto engine = std::make_shared<AcquisitionOnlyEngine>();
  const auto backend = ctk::clang_layer::make_match_backend(engine);
  const auto parsed = backend->parse(parse_request(), [] { return true; }, {});
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  ASSERT_NE(parsed.state, nullptr);
  EXPECT_TRUE(parsed.rows.empty());
  EXPECT_EQ(parsed.state->retained_bytes(), 0U);
  const auto again = backend->parse(parse_request(), [] { return true; }, {});
  ASSERT_EQ(again.code, MatchCode::Ok) << again.message;
  EXPECT_EQ(parsed.state->snapshot(), again.state->snapshot());
  EXPECT_EQ(engine->acquisitions, 2U);
  EXPECT_EQ(engine->matches, 0U);
  MatchRequest query;
  query.set_query("callExpr()");
  query.mutable_session()->set_session_id("unused-by-native-backend");
  const auto result =
      backend->execute(query, parsed.state, [] { return true; }, {});
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_EQ(result.rows.size(), 3U);
  EXPECT_EQ(parsed.state->snapshot(), result.state->snapshot());
  EXPECT_EQ(engine->acquisitions, 2U);
  EXPECT_EQ(engine->matches, 0U);
}

TEST_F(MatchCursors, CrossCategorySubtreeReturnsOwnedRowsAndSourceIndices) {
  auto first = run(file("functionDecl(hasName(\"alpha\")).bind(\"function\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  ASSERT_EQ(first.response.results_size(), 1);
  auto next =
      run(binding(first.response, "function", "callExpr().bind(\"call\")"));
  ASSERT_EQ(next.code, MatchCode::Ok) << next.message;
  EXPECT_EQ(next.response.session_id(), first.response.session_id());
  EXPECT_EQ(next.response.result_revision(), 2U);
  ASSERT_EQ(next.response.results_size(), 2);
  for (const auto &row : next.response.results()) {
    EXPECT_EQ(row.source_match_index(), 0U);
    EXPECT_TRUE(row.has_source_match_index());
    EXPECT_TRUE(row.bindings().at("call").node().has_call_expr());
    EXPECT_FALSE(row.bindings().contains("function"));
  }
  controller.reset();
  EXPECT_TRUE(
      next.response.results(0).bindings().at("call").node().has_call_expr());
}

TEST_F(MatchCursors, FailedQueriesAndStaleRevisionsPreservePriorBindings) {
  auto first = run(file("functionDecl(hasName(\"alpha\")).bind(\"function\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  EXPECT_EQ(run(session(first.response, "invalidMatcher()")).code,
            MatchCode::InvalidArgument);
  auto mismatch = session(first.response, "callExpr()");
  mismatch.mutable_session()->set_expected_result_revision(99);
  EXPECT_EQ(run(mismatch).code, MatchCode::Aborted);
  auto valid = run(binding(first.response, "function", "callExpr()"));
  EXPECT_EQ(valid.code, MatchCode::Ok) << valid.message;
  EXPECT_EQ(valid.response.result_revision(), 2U);
}

TEST_F(MatchCursors, WholeTreeRestartAndZeroMatchesAdvanceRevision) {
  auto first = run(file("functionDecl(hasName(\"missing\")).bind(\"f\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  EXPECT_EQ(first.response.result_revision(), 1U);
  EXPECT_EQ(first.response.results_size(), 0);
  auto restart = run(session(first.response, "callExpr().bind(\"call\")"));
  EXPECT_EQ(restart.code, MatchCode::Ok) << restart.message;
  EXPECT_EQ(restart.response.results_size(), 3);
  EXPECT_EQ(restart.response.result_revision(), 2U);
}

TEST_F(MatchCursors, RootOnlyDoesNotSearchDescendantsAndKeepsEmptyRows) {
  auto first = run(file("functionDecl(hasName(\"alpha\")).bind(\"f\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  auto request = binding(first.response, "f", "functionDecl()");
  request.mutable_binding()->set_scope(BINDING_MATCH_SCOPE_ROOT_ONLY);
  auto result = run(request);
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_EQ(result.response.results_size(), 1);
  EXPECT_TRUE(result.response.results(0).bindings().empty());
  EXPECT_EQ(result.response.results(0).source_match_index(), 0U);
  auto missing = run(binding(result.response, "f", "callExpr()"));
  EXPECT_EQ(missing.code, MatchCode::NotFound);
}

TEST_F(MatchCursors, ExactRowZeroAndIndependentCursorsSelectDistinctWorkflows) {
  auto first = run(file("functionDecl(isDefinition()).bind(\"f\")"));
  auto independent = run(file("functionDecl(hasName(\"alpha\")).bind(\"f\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  ASSERT_EQ(independent.code, MatchCode::Ok) << independent.message;
  EXPECT_NE(first.response.session_id(), independent.response.session_id());
  auto select = binding(first.response, "f", "callExpr()");
  select.mutable_binding()->set_match_index(0);
  auto zero = run(select);
  EXPECT_EQ(zero.code, MatchCode::Ok) << zero.message;
  EXPECT_EQ(zero.response.results_size(), 0);
  auto other = run(binding(independent.response, "f", "callExpr()"));
  EXPECT_EQ(other.code, MatchCode::Ok) << other.message;
  EXPECT_EQ(other.response.results_size(), 2);
}

TEST_F(MatchCursors, OverlappingRootsPreserveMultiplicity) {
  auto first =
      run(file("functionDecl(hasName(\"alpha\"), "
               "forEachDescendant(callExpr().bind(\"c\"))).bind(\"f\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  ASSERT_EQ(first.response.results_size(), 2);
  auto selected = run(binding(first.response, "f", "callExpr()"));
  ASSERT_EQ(selected.code, MatchCode::Ok) << selected.message;
  ASSERT_EQ(selected.response.results_size(), 4);
  EXPECT_EQ(selected.response.results(0).source_match_index(), 0U);
  EXPECT_EQ(selected.response.results(2).source_match_index(), 1U);
}

TEST_F(MatchCursors, QualifiedTypesPermitRootOnlyAndRejectSubtree) {
  auto first = run(
      file("varDecl(hasName(\"value\"), hasType(qualType().bind(\"type\")))"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  ASSERT_EQ(first.response.results_size(), 1);
  EXPECT_EQ(run(binding(first.response, "type", "qualType()")).code,
            MatchCode::FailedPrecondition);
  auto request = binding(first.response, "type", "qualType().bind(\"q\")");
  request.mutable_binding()->set_scope(BINDING_MATCH_SCOPE_ROOT_ONLY);
  auto selected = run(request);
  ASSERT_EQ(selected.code, MatchCode::Ok) << selected.message;
  ASSERT_EQ(selected.response.results_size(), 1);
  EXPECT_TRUE(
      selected.response.results(0).bindings().at("q").has_qualified_type());
}

TEST_F(MatchCursors, CancellationAndResultLimitsCommitNothing) {
  CursorSettings settings;
  settings.results.max_rows = 1;
  reset(settings);
  auto first = run(file("functionDecl(hasName(\"alpha\")).bind(\"f\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  auto cancelled = controller->match(
      "owner", session(first.response, "callExpr()"), [] { return false; });
  EXPECT_EQ(cancelled.code, MatchCode::Cancelled);
  EXPECT_EQ(run(binding(first.response, "f", "callExpr()")).code,
            MatchCode::ResourceExhausted);
  auto request = binding(first.response, "f", "functionDecl()");
  request.mutable_binding()->set_scope(BINDING_MATCH_SCOPE_ROOT_ONLY);
  auto valid = run(request);
  EXPECT_EQ(valid.code, MatchCode::Ok) << valid.message;
  EXPECT_EQ(valid.response.result_revision(), 2U);
}

TEST_F(MatchCursors, CallerScopeAndIdempotentCloseDoNotAffectOtherOwners) {
  auto first = run(file("callExpr().bind(\"c\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  EXPECT_EQ(run(session(first.response, "callExpr()"), "other").code,
            MatchCode::NotFound);
  EXPECT_EQ(controller->close("other", first.response.session_id()).code,
            MatchCode::Ok);
  EXPECT_EQ(run(session(first.response, "callExpr()")).code, MatchCode::Ok);
  EXPECT_EQ(controller->close("owner", first.response.session_id()).code,
            MatchCode::Ok);
  EXPECT_EQ(controller->close("owner", first.response.session_id()).code,
            MatchCode::Ok);
  EXPECT_EQ(run(session(first.response, "callExpr()"), "owner").code,
            MatchCode::NotFound);
  EXPECT_EQ(controller->close("owner", "invalid").code,
            MatchCode::InvalidArgument);
}

TEST_F(MatchCursors, ExpiryReclaimsCountCapacity) {
  CursorSettings settings;
  settings.max_cursors = 1;
  settings.idle_ttl = std::chrono::milliseconds(15);
  reset(settings);
  auto first = run(file("callExpr()"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  EXPECT_TRUE(first.response.has_expires_at());
  std::this_thread::sleep_for(std::chrono::milliseconds(25));
  EXPECT_EQ(run(session(first.response, "callExpr()")).code,
            MatchCode::NotFound);
  EXPECT_EQ(run(file("callExpr()")).code, MatchCode::Ok);
}

TEST_F(MatchCursors, MemoryBudgetRejectsPublication) {
  CursorSettings settings;
  settings.max_memory_bytes = 1;
  reset(settings);
  auto failed = run(file("callExpr()"));
  EXPECT_EQ(failed.code, MatchCode::ResourceExhausted);
  EXPECT_TRUE(failed.response.session_id().empty());
}

TEST_F(MatchCursors, ConcurrentRevisionGuardsAllowOnlyOneReplacement) {
  auto first = run(file("callExpr()"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  auto task = [&] { return run(session(first.response, "integerLiteral()")); };
  auto a = std::async(std::launch::async, task);
  auto b = std::async(std::launch::async, task);
  const auto left = a.get();
  const auto right = b.get();
  EXPECT_TRUE(
      (left.code == MatchCode::Ok && right.code == MatchCode::Aborted) ||
      (right.code == MatchCode::Ok && left.code == MatchCode::Aborted));
}

TEST_F(MatchCursors, PinnedGenerationSurvivesSourceChangeAndAnotherFileQuery) {
  auto first = run(file("integerLiteral().bind(\"n\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  std::ofstream(directory.path() / "fixture.cc") << "int changed=99;";
  auto fresh = run(file("integerLiteral().bind(\"n\")"));
  ASSERT_EQ(fresh.code, MatchCode::Ok) << fresh.message;
  ASSERT_EQ(fresh.response.results_size(), 1);
  auto old = run(session(first.response, "integerLiteral().bind(\"n\")"));
  ASSERT_EQ(old.code, MatchCode::Ok) << old.message;
  EXPECT_EQ(old.response.results_size(), 3);
  EXPECT_NE(old.response.results(0)
                .bindings()
                .at("n")
                .node()
                .integer_literal()
                .value()
                .unsigned_decimal(),
            "99");
}

TEST_F(MatchCursors, NativeSubtreeTraversalMatchesWholeTreePolicy) {
  std::ofstream(directory.path() / "fixture.cc")
      << "template<class T> T id(T x) { return x; }\n"
         "struct N { int x; bool operator==(const N&) const = default; };\n"
         "bool f(N a,N b) { auto l=[](int x){return x+1;}; return a!=b && "
         "id(l(2)); }";
  for (const auto mode :
       {MATCH_TRAVERSAL_MODE_AS_IS,
        MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE}) {
    auto root = file("translationUnitDecl().bind(\"root\")");
    auto first = run(root);
    ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
    auto whole = session(first.response, "expr().bind(\"e\")");
    whole.set_traversal_mode(mode);
    // Another independent cursor retains the same generation and root.
    auto second = run(root);
    auto subtree = binding(second.response, "root", "expr().bind(\"e\")");
    subtree.set_traversal_mode(mode);
    auto all = run(whole);
    auto within = run(subtree);
    ASSERT_EQ(all.code, MatchCode::Ok) << all.message;
    ASSERT_EQ(within.code, MatchCode::Ok) << within.message;
    EXPECT_EQ(all.response.results_size(), within.response.results_size());
    for (int i = 0; i < std::min(all.response.results_size(),
                                 within.response.results_size());
         ++i)
      EXPECT_EQ(
          all.response.results(i).bindings().at("e").SerializeAsString(),
          within.response.results(i).bindings().at("e").SerializeAsString());
  }
}

// A deterministic backend isolates the publication boundary from native
// parsing.
class PublicationState final : public ctk::clang_layer::NativeBindingState {
public:
  explicit PublicationState(ctk::cache::SnapshotPtr snapshot = {})
      : snapshot_(std::move(snapshot)) {}
  ctk::cache::SnapshotPtr snapshot() const override { return snapshot_; }
  std::size_t retained_bytes() const override { return 0; }

private:
  ctk::cache::SnapshotPtr snapshot_;
};
class PublicationBackend final : public ctk::clang_layer::IMatchBackend {
public:
  bool cancel_before_commit{};
  bool parse_with_rows{};
  bool *admitted{};
  ctk::cache::SnapshotPtr snapshot;
  ctk::clang_layer::MatchExecution
  parse(const ParseRequest &, const Checkpoint &,
        const ctk::clang_layer::MatchLimits &) override {
    if (cancel_before_commit && admitted)
      *admitted = false;
    ctk::clang_layer::MatchExecution result;
    result.state = std::make_shared<PublicationState>(snapshot);
    if (parse_with_rows)
      result.rows.emplace_back();
    return result;
  }
  ctk::clang_layer::MatchExecution
  execute(const MatchRequest &,
          std::shared_ptr<const ctk::clang_layer::NativeBindingState>,
          const Checkpoint &, const ctk::clang_layer::MatchLimits &) override {
    if (cancel_before_commit && admitted)
      *admitted = false;
    ctk::clang_layer::MatchExecution result;
    result.state = std::make_shared<PublicationState>(snapshot);
    result.rows.emplace_back();
    return result;
  }
};
MatchRequest publication_request() {
  MatchRequest request;
  request.set_query("decl()");
  request.mutable_file()->set_file_path("unused.cc");
  request.mutable_file()->set_working_directory("/tmp");
  return request;
}
ParseRequest publication_parse_request() {
  ParseRequest request;
  request.set_file_path("unused.cc");
  request.set_working_directory("/tmp");
  return request;
}
TEST(CursorPublication, ParseAndForkCancellationAtCommitConsumeNoCapacity) {
  CursorSettings settings;
  settings.max_cursors = 2;
  auto backend = std::make_shared<PublicationBackend>();
  MatchController controller(settings, backend);
  bool admitted = true;
  backend->admitted = &admitted;
  backend->cancel_before_commit = true;
  EXPECT_EQ(
      controller
          .parse("owner", publication_parse_request(), [&] { return admitted; })
          .code,
      MatchCode::Cancelled);
  admitted = true;
  backend->cancel_before_commit = false;
  const auto tree = controller.parse("owner", publication_parse_request(),
                                     [&] { return admitted; });
  ASSERT_EQ(tree.code, MatchCode::Ok) << tree.message;
  MatchRequest request;
  request.set_query("decl()");
  request.set_preserve_source(true);
  request.mutable_session()->set_session_id(tree.response.session_id());
  request.mutable_session()->set_expected_result_revision(1);
  backend->cancel_before_commit = true;
  EXPECT_EQ(controller.match("owner", request, [&] { return admitted; }).code,
            MatchCode::Cancelled);
  admitted = true;
  backend->cancel_before_commit = false;
  const auto fork =
      controller.match("owner", request, [&] { return admitted; });
  ASSERT_EQ(fork.code, MatchCode::Ok) << fork.message;
  EXPECT_NE(fork.response.session_id(), tree.response.session_id());
  EXPECT_EQ(fork.response.result_revision(), 1U);
  request.set_preserve_source(false);
  EXPECT_EQ(controller.match("owner", request, [&] { return admitted; }).code,
            MatchCode::Ok);
}
TEST(CursorPublication, ParseRejectsRowsAndEnvelopeLimitsAndStoppedAdmission) {
  auto backend = std::make_shared<PublicationBackend>();
  CursorSettings settings;
  settings.max_cursors = 1;
  MatchController controller(settings, backend);
  backend->parse_with_rows = true;
  EXPECT_EQ(
      controller
          .parse("owner", publication_parse_request(), [] { return true; })
          .code,
      MatchCode::Internal);
  backend->parse_with_rows = false;
  EXPECT_EQ(
      controller
          .parse("owner", publication_parse_request(), [] { return true; })
          .code,
      MatchCode::Ok);
  controller.stop_admission();
  EXPECT_EQ(
      controller
          .parse("owner", publication_parse_request(), [] { return true; })
          .code,
      MatchCode::ResourceExhausted);
  settings.results.max_bytes = 1;
  MatchController limited(settings, backend);
  const auto oversized =
      limited.parse("owner", publication_parse_request(), [] { return true; });
  EXPECT_EQ(oversized.code, MatchCode::ResourceExhausted);
  EXPECT_TRUE(oversized.response.session_id().empty());
}
TEST(CursorPublication, ForkMemoryAccountingChargesSharedSnapshotOnce) {
  CursorSettings settings;
  settings.max_memory_bytes = 8191;
  auto backend = std::make_shared<PublicationBackend>();
  ctk::cache::LoadedSnapshot loaded;
  loaded.owner = std::make_shared<ctk::cache::NativeSnapshotOwner>();
  loaded.inputs.push_back({"/ctk-test-shared.cc", ctk::cache::InputKind::File,
                           "fixture-digest", {}, {}});
  loaded.estimated_bytes = 4096;
  backend->snapshot = std::make_shared<ctk::cache::SnapshotEntry>(
      1, "same-native-generation", std::move(loaded));
  MatchController controller(settings, backend);
  const auto tree = controller.parse("owner", publication_parse_request(),
                                     [] { return true; });
  ASSERT_EQ(tree.code, MatchCode::Ok) << tree.message;
  MatchRequest request;
  request.set_query("decl()");
  request.set_preserve_source(true);
  request.mutable_session()->set_session_id(tree.response.session_id());
  request.mutable_session()->set_expected_result_revision(1);
  const auto first = controller.match("owner", request, [] { return true; });
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  EXPECT_EQ(controller.match("owner", request, [] { return true; }).code,
            MatchCode::Ok);
  EXPECT_EQ(controller.close("owner", tree.response.session_id()).code,
            MatchCode::Ok);
  request.mutable_session()->set_session_id(first.response.session_id());
  EXPECT_EQ(controller.match("owner", request, [] { return true; }).code,
            MatchCode::Ok);
}
class MatchOnlyBackend final : public ctk::clang_layer::IMatchBackend {
public:
  ctk::clang_layer::MatchExecution
  execute(const MatchRequest &,
          std::shared_ptr<const ctk::clang_layer::NativeBindingState>,
          const Checkpoint &, const ctk::clang_layer::MatchLimits &) override {
    return {};
  }
};
TEST(CursorPublication, BackendWithoutParseFailsWithoutInventingTree) {
  MatchController controller({}, std::make_shared<MatchOnlyBackend>());
  const auto reply = controller.parse("owner", publication_parse_request(),
                                      [] { return true; });
  EXPECT_EQ(reply.code, MatchCode::FailedPrecondition);
  EXPECT_TRUE(reply.response.session_id().empty());
}
TEST(CursorPublication, CancellationAtFinalCommitPreservesRevisionAndCapacity) {
  CursorSettings settings;
  settings.max_cursors = 1;
  auto backend = std::make_shared<PublicationBackend>();
  MatchController controller(settings, backend);
  bool admitted = true;
  backend->admitted = &admitted;
  backend->cancel_before_commit = true;
  auto request = publication_request();
  EXPECT_EQ(controller.match("owner", request, [&] { return admitted; }).code,
            MatchCode::Cancelled);
  admitted = true;
  backend->cancel_before_commit = false;
  auto first = controller.match("owner", request, [&] { return admitted; });
  ASSERT_EQ(first.code, MatchCode::Ok);
  request.mutable_session()->set_session_id(first.response.session_id());
  request.mutable_session()->set_expected_result_revision(1);
  backend->cancel_before_commit = true;
  EXPECT_EQ(controller.match("owner", request, [&] { return admitted; }).code,
            MatchCode::Cancelled);
  admitted = true;
  backend->cancel_before_commit = false;
  auto second = controller.match("owner", request, [&] { return admitted; });
  ASSERT_EQ(second.code, MatchCode::Ok);
  EXPECT_EQ(second.response.result_revision(), 2U);
}
TEST(CursorPublication, ResponseByteLimitIncludesEnvelopeAndEmptyRows) {
  CursorSettings settings;
  settings.results.max_bytes = 1;
  auto backend = std::make_shared<PublicationBackend>();
  MatchController controller(settings, backend);
  auto reply =
      controller.match("owner", publication_request(), [] { return true; });
  EXPECT_EQ(reply.code, MatchCode::ResourceExhausted);
  EXPECT_TRUE(reply.response.session_id().empty());
}
TEST(CursorPublication, CloseReclaimsCapacityAndInvalidTargetsAreRejected) {
  CursorSettings settings;
  settings.max_cursors = 1;
  auto backend = std::make_shared<PublicationBackend>();
  MatchController controller(settings, backend);
  auto request = publication_request();
  auto first = controller.match("owner", request, [] { return true; });
  ASSERT_EQ(first.code, MatchCode::Ok);
  EXPECT_EQ(controller.match("owner", request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
  EXPECT_EQ(controller.close("owner", first.response.session_id()).code,
            MatchCode::Ok);
  EXPECT_EQ(controller.match("owner", request, [] { return true; }).code,
            MatchCode::Ok);
  request.set_traversal_mode(static_cast<MatchTraversalMode>(99));
  EXPECT_EQ(controller.match("owner", request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  request.set_traversal_mode(MATCH_TRAVERSAL_MODE_AS_IS);
  request.mutable_file()->add_compile_arguments("-std=c17");
  EXPECT_EQ(controller.match("owner", request, [] { return true; }).code,
            MatchCode::InvalidArgument);
  controller.stop_admission();
  request.mutable_file()->clear_compile_arguments();
  EXPECT_EQ(controller.match("owner", request, [] { return true; }).code,
            MatchCode::ResourceExhausted);
}
} // namespace
} // namespace ctk::application
