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
  MatchReply stream(const MatchRequest &request,
                    const MatchController::StreamSink &sink,
                    std::string owner = "owner") {
    return controller->stream_match(owner, request, [] { return true; }, sink);
  }
};

TEST_F(MatchCursors, StreamEmitsFullRowsThenCommitsThinContinuationState) {
  std::vector<MatchStreamEvent> events;
  std::promise<void> first_row;
  std::promise<void> release_sink;
  auto release = release_sink.get_future();
  bool blocked_first_row = false;
  auto pending = std::async(std::launch::async, [this, &events, &first_row,
                                                 &release, &blocked_first_row] {
    return stream(file("functionDecl().bind(\"f\")"),
                  [&events, &first_row, &release, &blocked_first_row](
                      const MatchStreamEvent &event, std::string &) {
                    events.push_back(event);
                    if (event.has_row() && !blocked_first_row) {
                      blocked_first_row = true;
                      first_row.set_value();
                      release.wait();
                    }
                    return MatchCode::Ok;
                  });
  });
  const auto arrived = first_row.get_future().wait_for(std::chrono::seconds(5));
  EXPECT_EQ(arrived, std::future_status::ready);
  EXPECT_EQ(pending.wait_for(std::chrono::seconds(0)),
            std::future_status::timeout);
  release_sink.set_value();
  const auto result = pending.get();
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_EQ(events.size(), 4U);
  for (int i = 0; i < 3; ++i) {
    ASSERT_TRUE(events[i].has_row());
    const auto &binding = events[i].row().bindings().at("f");
    EXPECT_TRUE(binding.has_node());
    EXPECT_NE(binding.supported_scopes_size(), 0);
  }
  ASSERT_TRUE(events.back().has_completed());
  const auto &completion = events.back().completed();
  EXPECT_EQ(completion.session_id(), result.response.session_id());
  EXPECT_EQ(completion.result_revision(), 1U);
  EXPECT_EQ(completion.row_count(), 3U);

  // The retained revision carries only selector metadata, while native
  // bindings remain available for later continuation.
  for (const auto &row : result.response.results()) {
    ASSERT_TRUE(row.bindings().contains("f"));
    EXPECT_FALSE(row.bindings().at("f").has_node() ||
                 row.bindings().at("f").has_qualified_type() ||
                 row.bindings().at("f").has_unsupported());
    EXPECT_NE(row.bindings().at("f").supported_scopes_size(), 0);
  }
  auto next = binding(result.response, "f", "callExpr().bind(\"call\")");
  const auto continued = run(next);
  ASSERT_EQ(continued.code, MatchCode::Ok) << continued.message;
  ASSERT_EQ(continued.response.results_size(), 3);
  EXPECT_EQ(continued.response.results(0).source_match_index(), 1U);
  EXPECT_EQ(continued.response.results(2).source_match_index(), 2U);
}

TEST_F(MatchCursors, StreamZeroRowsCompletesAndCancellationDoesNotCommit) {
  std::vector<MatchStreamEvent> empty_events;
  auto empty =
      stream(file("functionDecl(hasName(\"missing\"))"),
             [&empty_events](const MatchStreamEvent &event, std::string &) {
               empty_events.push_back(event);
               return MatchCode::Ok;
             });
  ASSERT_EQ(empty.code, MatchCode::Ok) << empty.message;
  ASSERT_EQ(empty_events.size(), 1U);
  ASSERT_TRUE(empty_events.front().has_completed());
  EXPECT_EQ(empty_events.front().completed().row_count(), 0U);

  const auto source = run(file("functionDecl().bind(\"f\")"));
  ASSERT_EQ(source.code, MatchCode::Ok) << source.message;
  auto continuation = binding(source.response, "f", "callExpr()");
  int rows_seen = 0;
  const auto cancelled =
      stream(continuation,
             [&rows_seen](const MatchStreamEvent &event, std::string &message) {
               if (event.has_row()) {
                 ++rows_seen;
                 message = "test stream stopped";
                 return MatchCode::Cancelled;
               }
               return MatchCode::Ok;
             });
  EXPECT_EQ(cancelled.code, MatchCode::Cancelled);
  EXPECT_EQ(rows_seen, 1);
  continuation = binding(source.response, "f", "callExpr()");
  const auto retry = run(continuation);
  ASSERT_EQ(retry.code, MatchCode::Ok) << retry.message;
  EXPECT_EQ(retry.response.result_revision(), 2U);
}

TEST_F(MatchCursors,
       FollowupNativeMatcherFindsChildAndReturnsItsShallowProjection) {
  std::ofstream(directory.path() / "fixture.cc")
      << "int parent() { return 4 + 1; }\n";
  const auto parent = run(file("functionDecl(hasName(\"parent\")).bind(\"f\")"));
  ASSERT_EQ(parent.code, MatchCode::Ok) << parent.message;
  ASSERT_EQ(parent.response.results_size(), 1);
  const auto &function = parent.response.results(0).bindings().at("f");
  ASSERT_TRUE(function.has_node());
  EXPECT_FALSE(function.node().function_decl().function().has_body());
  EXPECT_TRUE(function.is_complete());

  const auto child_request =
      binding(parent.response, "f", "binaryOperator().bind(\"child\")");
  const auto child_result = run(child_request);
  ASSERT_EQ(child_result.code, MatchCode::Ok) << child_result.message;
  ASSERT_EQ(child_result.response.results_size(), 1);
  const auto &child = child_result.response.results(0).bindings().at("child");
  ASSERT_TRUE(child.has_node());
  const auto &binary = child.node().binary_operator();
  EXPECT_EQ(binary.opcode(), ctk::ast::v1::BINARY_OPCODE_ADD);
  EXPECT_FALSE(binary.has_left());
  EXPECT_FALSE(binary.has_right());
  EXPECT_TRUE(child.is_complete());
  bool left_unrequested = false;
  bool right_unrequested = false;
  for (const auto &entry : child.availability()) {
    if (entry.state() != ctk::ast::v1::FIELD_STATE_UNREQUESTED)
      continue;
    left_unrequested |= entry.field_path().ends_with("left");
    right_unrequested |= entry.field_path().ends_with("right");
  }
  EXPECT_TRUE(left_unrequested);
  EXPECT_TRUE(right_unrequested);
}

TEST_F(MatchCursors, StreamUsesPerEventBudgetWhileUnaryKeepsAggregateLimit) {
  CursorSettings settings;
  settings.results.max_bytes = 4096;
  reset(settings);
  std::ofstream source(directory.path() / "fixture.cc");
  for (int i = 0; i < 24; ++i)
    source << "struct StreamRecord" << i << " { int member" << i << "; };\n";
  source.close();
  const auto request = file("recordDecl().bind(\"record\")");
  EXPECT_EQ(run(request).code, MatchCode::ResourceExhausted);
  std::size_t transmitted = 0;
  const auto streamed = stream(
      request, [&transmitted](const MatchStreamEvent &event, std::string &) {
        transmitted += event.ByteSizeLong();
        EXPECT_LE(event.ByteSizeLong(), 4096U);
        return MatchCode::Ok;
      });
  ASSERT_EQ(streamed.code, MatchCode::Ok) << streamed.message;
  EXPECT_GT(transmitted, 4096U);
  EXPECT_EQ(streamed.response.results_size(), 48);
}

TEST_F(MatchCursors, LegacyUnaryKeepsFullRowsAndContinuesFromThinRetention) {
  const auto first = run(file("functionDecl(hasName(\"alpha\")).bind(\"f\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  ASSERT_EQ(first.response.results_size(), 1);
  EXPECT_TRUE(first.response.results(0).bindings().at("f").has_node());

  const auto next = run(binding(first.response, "f", "callExpr().bind(\"c\")"));
  ASSERT_EQ(next.code, MatchCode::Ok) << next.message;
  EXPECT_EQ(next.response.results_size(), 2);
}

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

TEST_F(MatchCursors, ByteLimitReportsBudgetAndPreservesParsedTree) {
  CursorSettings settings;
  settings.results.max_bytes = 128;
  reset(settings);
  const auto parsed =
      controller->parse("owner", parse_request(), [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  const auto tree = tree_response(parsed.response);
  const auto rejected = fork(session(tree, "functionDecl().bind(\"f\")"));
  ASSERT_EQ(rejected.code, MatchCode::ResourceExhausted);
  EXPECT_NE(rejected.message.find("limit 128 bytes"), std::string::npos);
  EXPECT_NE(rejected.message.find("next row"), std::string::npos);
  EXPECT_NE(rejected.message.find("server.grpc.max_send_message_bytes"),
            std::string::npos);
  EXPECT_NE(rejected.message.find("no cursor state committed"),
            std::string::npos);
  EXPECT_EQ(fork(session(tree, "functionDecl(hasName(\"absent\"))")).code,
            MatchCode::Ok);
}

TEST_F(MatchCursors, DefaultBudgetAcceptsIncludedResultsLargerThan64MiB) {
  std::ofstream header(directory.path() / "many.hpp");
  for (int index = 0; index < 15000; ++index)
    header << "void function_" << index << "_" << std::string(1000, 'x')
           << "();\n";
  header.close();
  std::ofstream source(directory.path() / "fixture.cc");
  source << "#include \"many.hpp\"\nvoid source_function();\n";
  source.close();
  const auto parsed =
      controller->parse("owner", parse_request(), [] { return true; });
  ASSERT_EQ(parsed.code, MatchCode::Ok) << parsed.message;
  const auto result = fork(
      session(tree_response(parsed.response), "functionDecl().bind(\"x\")"));
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  EXPECT_EQ(result.response.results_size(), 15001);
  EXPECT_GT(result.response.ByteSizeLong(), 64U * 1024 * 1024);
  EXPECT_TRUE(result.response.results(0).bindings().contains("root"));
  EXPECT_TRUE(result.response.results(0).bindings().contains("x"));
}

TEST_F(MatchCursors, AutomaticRootMatchesClangQueryAndIncludesHeaders) {
  std::ofstream(directory.path() / "included.hpp")
      << "void header_function();\n";
  std::ofstream(directory.path() / "fixture.cc")
      << "#include \"included.hpp\"\nvoid source_function();\n";
  auto unbound = run(file("functionDecl()"));
  ASSERT_EQ(unbound.code, MatchCode::Ok) << unbound.message;
  ASSERT_EQ(unbound.response.results_size(), 2);
  for (const auto &row : unbound.response.results()) {
    ASSERT_EQ(row.bindings().size(), 1U);
    EXPECT_TRUE(row.bindings().at("root").node().has_function_decl());
  }
  auto named = run(file("functionDecl().bind(\"x\")"));
  ASSERT_EQ(named.code, MatchCode::Ok) << named.message;
  ASSERT_EQ(named.response.results_size(), 2);
  for (const auto &row : named.response.results()) {
    ASSERT_EQ(row.bindings().size(), 2U);
    EXPECT_EQ(row.bindings().at("root").SerializeAsString(),
              row.bindings().at("x").SerializeAsString());
  }
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

TEST_F(MatchCursors, RootOnlyDoesNotSearchDescendantsAndBindsRoot) {
  auto first = run(file("functionDecl(hasName(\"alpha\")).bind(\"f\")"));
  ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
  auto request = binding(first.response, "f", "functionDecl()");
  request.mutable_binding()->set_scope(BINDING_MATCH_SCOPE_ROOT_ONLY);
  auto result = run(request);
  ASSERT_EQ(result.code, MatchCode::Ok) << result.message;
  ASSERT_EQ(result.response.results_size(), 1);
  EXPECT_EQ(result.response.results(0).bindings().size(), 1U);
  EXPECT_TRUE(result.response.results(0).bindings().contains("root"));
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
         "bool f(N a,N b) { int values[] = {3,4}; int total=0; "
         "for (int value : values) total += value; "
         "auto l=[](int x){return x+1;}; return a!=b && "
         "id(l(2)); }";
  for (const auto mode :
       {MATCH_TRAVERSAL_MODE_AS_IS,
        MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE}) {
    const auto compare_scopes = [&](const std::string &query,
                                    const std::string &bind) {
      auto first = run(file("translationUnitDecl().bind(\"root\")"));
      ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
      auto whole = session(first.response, query);
      whole.set_traversal_mode(mode);
      auto second = run(file("translationUnitDecl().bind(\"root\")"));
      ASSERT_EQ(second.code, MatchCode::Ok) << second.message;
      auto subtree = binding(second.response, "root", query);
      subtree.set_traversal_mode(mode);
      auto all = run(whole);
      auto within = run(subtree);
      ASSERT_EQ(all.code, MatchCode::Ok) << all.message;
      ASSERT_EQ(within.code, MatchCode::Ok) << within.message;
      ASSERT_EQ(all.response.results_size(), within.response.results_size());
      for (int index = 0; index < all.response.results_size(); ++index)
        EXPECT_EQ(all.response.results(index)
                      .bindings()
                      .at(bind)
                      .SerializeAsString(),
                  within.response.results(index)
                      .bindings()
                      .at(bind)
                      .SerializeAsString());
    };
    compare_scopes("expr().bind(\"e\")", "e");
    compare_scopes("stmt().bind(\"s\")", "s");
    compare_scopes("decl().bind(\"d\")", "d");
  }
}

TEST_F(MatchCursors, SelectedDeclAndStmtRootsStayInsideTheirSubtrees) {
  std::ofstream(directory.path() / "fixture.cc")
      << "template<class T> T id(T x) { return x; }\n"
         "int chosen() { auto l=[](int x){return id(x+1);}; return l(2); }\n"
         "int unrelated() { return id(999); }\n";

  for (const auto mode :
       {MATCH_TRAVERSAL_MODE_AS_IS,
        MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE}) {
    auto first = run(file("functionDecl(hasName(\"chosen\")).bind(\"f\")"));
    ASSERT_EQ(first.code, MatchCode::Ok) << first.message;
    auto selected = binding(
        first.response, "f",
        "callExpr(hasAncestor(functionDecl(hasName(\"chosen\")))).bind(\"c\")");
    selected.set_traversal_mode(mode);
    auto calls = run(selected);
    ASSERT_EQ(calls.code, MatchCode::Ok) << calls.message;
    ASSERT_EQ(calls.response.results_size(), 2);
    int plain_calls = 0;
    int operator_calls = 0;
    for (const auto &row : calls.response.results()) {
      EXPECT_EQ(row.source_match_index(), 0U);
      const auto &node = row.bindings().at("c").node();
      plain_calls += node.has_call_expr();
      operator_calls += node.has_cxx_operator_call_expr();
    }
    EXPECT_EQ(plain_calls, 1);
    EXPECT_EQ(operator_calls, 1);

    auto operator_source =
        run(file("functionDecl(hasName(\"chosen\")).bind(\"f\")"));
    ASSERT_EQ(operator_source.code, MatchCode::Ok) << operator_source.message;
    auto operator_query = binding(operator_source.response, "f",
                                  "cxxOperatorCallExpr().bind(\"call\")");
    operator_query.set_traversal_mode(mode);
    auto operator_result = run(operator_query);
    ASSERT_EQ(operator_result.code, MatchCode::Ok) << operator_result.message;
    ASSERT_EQ(operator_result.response.results_size(), 1);
    EXPECT_TRUE(operator_result.response.results(0)
                    .bindings()
                    .at("call")
                    .node()
                    .has_cxx_operator_call_expr());

    auto statement_source =
        run(file("functionDecl(hasName(\"chosen\")).bind(\"f\")"));
    ASSERT_EQ(statement_source.code, MatchCode::Ok) << statement_source.message;
    auto statement =
        binding(statement_source.response, "f",
                "binaryOperator(hasOperatorName(\"+\")).bind(\"sum\")");
    statement.set_traversal_mode(mode);
    auto sums = run(statement);
    ASSERT_EQ(sums.code, MatchCode::Ok) << sums.message;
    ASSERT_EQ(sums.response.results_size(), 1);
    auto literals = binding(sums.response, "sum", "integerLiteral().bind(\"n\")");
    literals.set_traversal_mode(mode);
    auto within_statement = run(literals);
    ASSERT_EQ(within_statement.code, MatchCode::Ok) << within_statement.message;
    ASSERT_EQ(within_statement.response.results_size(), 1);
    EXPECT_EQ(within_statement.response.results(0).source_match_index(), 0U);
    EXPECT_EQ(within_statement.response.results(0)
                  .bindings()
                  .at("n")
                  .node()
                  .integer_literal()
                  .value()
                  .unsigned_decimal(),
              "1");
  }
}

TEST_F(MatchCursors, TypedefAwareInheritanceMatcherKeepsWholeTreeAliases) {
  std::ofstream(directory.path() / "fixture.cc")
      << "struct Base {};\n"
         "using Alias = Base;\n"
         "struct Derived : Alias {};\n";
  auto whole =
      run(file("cxxRecordDecl(isDerivedFrom(\"Alias\")).bind(\"d\")"));
  ASSERT_EQ(whole.code, MatchCode::Ok) << whole.message;
  ASSERT_EQ(whole.response.results_size(), 1);

  auto selected =
      run(file("cxxRecordDecl(hasName(\"Derived\")).bind(\"root\")"));
  ASSERT_EQ(selected.code, MatchCode::Ok) << selected.message;
  auto continuation =
      binding(selected.response, "root",
              "cxxRecordDecl(isDerivedFrom(\"Alias\")).bind(\"d\")");
  auto within = run(continuation);
  ASSERT_EQ(within.code, MatchCode::Ok) << within.message;
  ASSERT_EQ(within.response.results_size(), 1);
  EXPECT_EQ(within.response.results(0).bindings().at("d").SerializeAsString(),
            whole.response.results(0).bindings().at("d").SerializeAsString());
}

TEST_F(MatchCursors, ConstructorSubtreeVisitsOnlyItsDefaultInitializerNodes) {
  std::ofstream(directory.path() / "fixture.cc")
      << "struct Defaults { int zero = 0; int one = 1; "
         "Defaults(); explicit Defaults(int); };\n"
         "Defaults::Defaults() {}\n"
         "Defaults::Defaults(int) {}\n";

  // The initializer expression nodes are shared by the field and both
  // constructor occurrences. A selected constructor walk visits only its own
  // two CXXDefaultInitExpr subtrees, once each, in field order.
  for (const auto *query : {
           "cxxConstructorDecl(hasName(\"Defaults\"), isDefinition(), "
           "unless(isImplicit()), parameterCountIs(0)).bind(\"ctor\")",
           "cxxConstructorDecl(hasName(\"Defaults\"), isDefinition(), "
           "unless(isImplicit()), parameterCountIs(1)).bind(\"ctor\")"}) {
    auto selected = run(file(query));
    ASSERT_EQ(selected.code, MatchCode::Ok) << selected.message;
    ASSERT_EQ(selected.response.results_size(), 1);
    auto within = run(binding(selected.response, "ctor",
                              "integerLiteral().bind(\"n\")"));
    ASSERT_EQ(within.code, MatchCode::Ok) << within.message;
    ASSERT_EQ(within.response.results_size(), 2);
    EXPECT_EQ(within.response.results(0).bindings().at("n")
                  .node()
                  .integer_literal()
                  .value()
                  .unsigned_decimal(),
              "0");
    EXPECT_EQ(within.response.results(1).bindings().at("n")
                  .node()
                  .integer_literal()
                  .value()
                  .unsigned_decimal(),
              "1");
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
  loaded.inputs.push_back({"/ctk-test-shared.cc",
                           ctk::cache::InputKind::File,
                           "fixture-digest",
                           {},
                           {}});
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
