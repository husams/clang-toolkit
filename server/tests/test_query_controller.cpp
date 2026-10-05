#include "ctk/application/query.hpp"
#include "ctk/clang/tooling.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <functional>
#include <mutex>
#include <set>

namespace ctk::application {
namespace {
class FakeQueryEngine final : public ctk::clang_layer::IQueryEngine {
public:
  ctk::clang_layer::QueryResult match(const ctk::clang_layer::FileInput &file,
                                      const std::string &query,
                                      const Checkpoint &checkpoint,
                                      const MatchCallback &on_match) override {
    ++calls;
    observed_query = query;
    observed_files.insert(file.path);
    if (before_match)
      before_match();
    if (!checkpoint())
      return {false, true, false, "", "cancelled", 0};
    on_match({{"decl", {"FunctionDecl", "analyzed", "int ()"}}});
    return {true, false, true, "test-profile", {}, 4096};
  }

  std::atomic<int> calls{0};
  std::string observed_query;
  std::set<std::string> observed_files;
  std::function<void()> before_match;
};

class RecordingSink final : public IQueryEventSink {
public:
  bool publish(QueryEvent event) override {
    std::lock_guard lock(mutex);
    events.push_back(std::move(event));
    cv.notify_all();
    return true;
  }
  void on_complete(Outcome result) override {
    std::lock_guard lock(mutex);
    outcome = std::move(result);
    completed = true;
    cv.notify_all();
  }
  bool wait_for_completion() {
    std::unique_lock lock(mutex);
    return cv.wait_for(lock, std::chrono::seconds(5),
                       [&] { return completed; });
  }
  bool wait_for_event(EventKind kind) {
    std::unique_lock lock(mutex);
    return cv.wait_for(lock, std::chrono::seconds(5), [&] {
      return std::any_of(
          events.begin(), events.end(),
          [kind](const auto &item) { return item.kind == kind; });
    });
  }
  std::vector<QueryEvent> snapshot() {
    std::lock_guard lock(mutex);
    return events;
  }
  Outcome final_outcome() {
    std::lock_guard lock(mutex);
    return outcome;
  }

  std::mutex mutex;
  std::condition_variable cv;
  std::vector<QueryEvent> events;
  Outcome outcome;
  bool completed = false;
};

FileInput file(std::string path) {
  FileInput input;
  input.path = std::move(path);
  input.working_directory = "/tmp";
  input.compile_arguments = {"-std=c++20"};
  return input;
}

TEST(QueryController,
     FixedQueryPublishesNativeBindingsAndCompletesAfterAllFiles) {
  auto engine = std::make_shared<FakeQueryEngine>();
  QueryController controller({}, engine);
  auto sink = std::make_shared<RecordingSink>();

  QueryRequest request;
  request.query = "functionDecl().bind(\"decl\")";
  request.files = {file("one.cc"), file("two.cc")};
  auto handle = controller.start(std::move(request), sink);

  ASSERT_TRUE(sink->wait_for_completion());
  handle->transport_done();
  EXPECT_EQ(sink->final_outcome().code, OutcomeCode::Ok);
  EXPECT_EQ(engine->calls.load(), 2);
  EXPECT_EQ(engine->observed_query, "functionDecl().bind(\"decl\")");
  const auto events = sink->snapshot();
  EXPECT_EQ(std::count_if(events.begin(), events.end(),
                          [](const auto &item) {
                            return item.kind == EventKind::Match &&
                                   item.bindings.contains("decl");
                          }),
            2);
  const auto complete =
      std::find_if(events.begin(), events.end(), [](const auto &item) {
        return item.kind == EventKind::Completed;
      });
  ASSERT_NE(complete, events.end());
  EXPECT_EQ(complete->completed_files, 2);
  EXPECT_EQ(complete->match_count, 2);
  const auto queued =
      std::find_if(events.begin(), events.end(), [](const auto &item) {
        return item.kind == EventKind::Queued;
      });
  const auto started =
      std::find_if(events.begin(), events.end(), [](const auto &item) {
        return item.kind == EventKind::Started;
      });
  ASSERT_NE(queued, events.end());
  ASSERT_NE(started, events.end());
  EXPECT_LT(queued, started);
}

TEST(QueryController, RejectsWholeBatchAndKeepsEarlierAcceptedWorkRunning) {
  auto engine = std::make_shared<FakeQueryEngine>();
  ControllerSettings settings;
  settings.max_files = 1;
  settings.max_memory_bytes = 16ULL * 1024 * 1024;
  settings.overhead_memory_bytes = 49ULL * 1024 * 1024;
  QueryController controller(settings, engine);
  auto sink = std::make_shared<RecordingSink>();
  auto handle = controller.open(sink);

  handle->submit({"q", CommandKind::StartQuery, "functionDecl()", {}});
  handle->submit({"a", CommandKind::AddFiles, {}, {file("accepted.cc")}});
  handle->submit({"b",
                  CommandKind::AddFiles,
                  {},
                  {file("rejected.cc"), file("also-rejected.cc")}});
  handle->submit({"m", CommandKind::Match, {}, {}});
  handle->close_input();

  ASSERT_TRUE(sink->wait_for_completion());
  handle->transport_done();
  EXPECT_EQ(sink->final_outcome().code, OutcomeCode::Ok);
  EXPECT_EQ(engine->calls.load(), 1);
  const auto events = sink->snapshot();
  const auto rejected =
      std::find_if(events.begin(), events.end(), [](const auto &item) {
        return item.kind == EventKind::Rejected && item.request_id == "b";
      });
  ASSERT_NE(rejected, events.end());
  ASSERT_EQ(rejected->outcome.violations.size(), 3);
  EXPECT_EQ(rejected->outcome.violations[0].limit_name, "session.max_files");
  EXPECT_EQ(rejected->outcome.violations[1].limit_name,
            "session.max_memory_bytes");
  EXPECT_EQ(rejected->outcome.violations[2].limit_name,
            "session.overhead_memory_bytes");
  for (const auto &violation : rejected->outcome.violations) {
    EXPECT_GT(violation.current_value, 0U);
    EXPECT_GT(violation.projected_value, violation.configured_limit);
  }
}

TEST(QueryController, InitialAdmissionFailureCompletesWithResourceExhausted) {
  auto engine = std::make_shared<FakeQueryEngine>();
  ControllerSettings settings;
  settings.max_files = 1;
  settings.max_memory_bytes = 1;
  settings.overhead_memory_bytes = 1;
  QueryController controller(settings, engine);
  auto sink = std::make_shared<RecordingSink>();
  QueryRequest request;
  request.query = "functionDecl()";
  request.files = {file("first.cc"), file("second.cc")};

  auto handle = controller.start(std::move(request), sink);
  ASSERT_TRUE(sink->wait_for_completion());
  handle->transport_done();
  EXPECT_EQ(sink->final_outcome().code, OutcomeCode::ResourceExhausted);
  ASSERT_EQ(sink->final_outcome().violations.size(), 3);
  EXPECT_EQ(engine->calls.load(), 0);
}

TEST(QueryController, CancellingBeforeMatchReleasesFileAdmission) {
  auto engine = std::make_shared<FakeQueryEngine>();
  ControllerSettings settings;
  settings.max_files = 1;
  settings.max_memory_bytes = 16ULL * 1024 * 1024;
  settings.overhead_memory_bytes = 100ULL * 1024 * 1024;
  QueryController controller(settings, engine);
  auto cancelled_sink = std::make_shared<RecordingSink>();
  auto handle = controller.open(cancelled_sink);
  handle->submit({"q", CommandKind::StartQuery, "functionDecl()", {}});
  handle->submit({"a", CommandKind::AddFiles, {}, {file("reserved.cc")}});
  handle->cancel();
  ASSERT_TRUE(cancelled_sink->wait_for_completion());
  handle->transport_done();

  auto next_sink = std::make_shared<RecordingSink>();
  QueryRequest request;
  request.query = "functionDecl()";
  request.files = {file("next.cc")};
  auto next_handle = controller.start(std::move(request), next_sink);
  ASSERT_TRUE(next_sink->wait_for_completion());
  next_handle->transport_done();
  EXPECT_EQ(next_sink->final_outcome().code, OutcomeCode::Ok);
  EXPECT_EQ(engine->calls.load(), 1);
}

TEST(QueryController,
     CancellationDuringBatchCompletesWithoutCountingUnstartedFiles) {
  auto engine = std::make_shared<FakeQueryEngine>();
  std::mutex gate_mutex;
  std::condition_variable gate_cv;
  bool entered = false;
  bool released = false;
  engine->before_match = [&] {
    std::unique_lock lock(gate_mutex);
    entered = true;
    gate_cv.notify_all();
    gate_cv.wait(lock, [&] { return released; });
  };
  QueryController controller({}, engine);
  auto sink = std::make_shared<RecordingSink>();
  QueryRequest request;
  request.query = "functionDecl()";
  request.files = {file("running.cc"), file("unstarted.cc")};
  auto handle = controller.start(std::move(request), sink);

  {
    std::unique_lock lock(gate_mutex);
    ASSERT_TRUE(gate_cv.wait_for(lock, std::chrono::seconds(5),
                                 [&] { return entered; }));
  }
  handle->cancel();
  {
    std::lock_guard lock(gate_mutex);
    released = true;
  }
  gate_cv.notify_all();

  ASSERT_TRUE(sink->wait_for_completion());
  handle->transport_done();
  EXPECT_EQ(sink->final_outcome().code, OutcomeCode::Cancelled);
  const auto events = sink->snapshot();
  const auto complete =
      std::find_if(events.begin(), events.end(), [](const auto &item) {
        return item.kind == EventKind::Completed;
      });
  ASSERT_NE(complete, events.end());
  EXPECT_EQ(complete->completed_files, 0);
}

TEST(QueryController, ResumeAndCancelWakePausedWorkers) {
  auto engine = std::make_shared<FakeQueryEngine>();
  QueryController controller({}, engine);
  auto resumed_sink = std::make_shared<RecordingSink>();
  auto resumed = controller.open(resumed_sink);
  resumed->submit({"q1", CommandKind::StartQuery, "functionDecl()", {}});
  resumed->submit({"a1", CommandKind::AddFiles, {}, {file("resume.cc")}});
  resumed->submit({"p1", CommandKind::Pause, {}, {}});
  resumed->submit({"m1", CommandKind::Match, {}, {}});
  resumed->close_input();
  ASSERT_TRUE(resumed_sink->wait_for_event(EventKind::Started));
  std::atomic<bool> consumed{false};
  resumed->submit({"r1", CommandKind::Resume, {}, {}},
                  [&] { consumed.store(true); });
  ASSERT_TRUE(resumed_sink->wait_for_completion());
  resumed->transport_done();
  EXPECT_TRUE(consumed.load());
  EXPECT_EQ(resumed_sink->final_outcome().code, OutcomeCode::Ok);

  auto cancelled_sink = std::make_shared<RecordingSink>();
  auto cancelled = controller.open(cancelled_sink);
  cancelled->submit({"q2", CommandKind::StartQuery, "functionDecl()", {}});
  cancelled->submit(
      {"a2", CommandKind::AddFiles, {}, {file("cancel-paused.cc")}});
  cancelled->submit({"p2", CommandKind::Pause, {}, {}});
  cancelled->submit({"m2", CommandKind::Match, {}, {}});
  cancelled->close_input();
  ASSERT_TRUE(cancelled_sink->wait_for_event(EventKind::Started));
  cancelled->cancel();
  ASSERT_TRUE(cancelled_sink->wait_for_completion());
  cancelled->transport_done();
  EXPECT_EQ(cancelled_sink->final_outcome().code, OutcomeCode::Cancelled);
}

TEST(QueryController, StopAdmissionClosesStreamsButDrainsAcceptedWork) {
  auto engine = std::make_shared<FakeQueryEngine>();
  std::mutex gate_mutex;
  std::condition_variable gate_cv;
  bool entered = false;
  bool released = false;
  engine->before_match = [&] {
    std::unique_lock lock(gate_mutex);
    entered = true;
    gate_cv.notify_all();
    gate_cv.wait(lock, [&] { return released; });
  };
  QueryController controller({}, engine);
  auto sink = std::make_shared<RecordingSink>();
  auto handle = controller.open(sink);
  handle->submit({"q", CommandKind::StartQuery, "functionDecl()", {}});
  handle->submit(
      {"a", CommandKind::AddFiles, {}, {file("accepted-on-shutdown.cc")}});
  handle->submit({"m", CommandKind::Match, {}, {}});
  {
    std::unique_lock lock(gate_mutex);
    ASSERT_TRUE(gate_cv.wait_for(lock, std::chrono::seconds(5),
                                 [&] { return entered; }));
  }
  controller.stop_admission();
  {
    std::lock_guard lock(gate_mutex);
    released = true;
  }
  gate_cv.notify_all();
  ASSERT_TRUE(sink->wait_for_completion());
  handle->transport_done();
  EXPECT_EQ(sink->final_outcome().code, OutcomeCode::Ok);
}

} // namespace
} // namespace ctk::application
