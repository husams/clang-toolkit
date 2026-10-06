#include "ctk/clang/tooling.hpp"
#include "ctk/net/outbound_event_queue.hpp"
#include "ctk/net/protocol_adapter.hpp"
#include "ctk/net/server.hpp"
#include <atomic>
#include <chrono>
#include <filesystem>
#include <future>
#include <grpcpp/create_channel.h>
#include <grpcpp/security/credentials.h>
#include <gtest/gtest.h>
#include <thread>

namespace {
namespace app = ctk::application;
namespace wire = ctk::query::v1;

TEST(EventEncoder, CopiesTypedMatchBindingAlongsideLegacySummary) {
  app::QueryEvent event{app::EventKind::Match};
  event.request_id = "query-1";
  auto &binding = event.bindings["literal"];
  binding.kind = "IntegerLiteral";
  binding.name = "42";
  binding.type = "int";
  binding.value.mutable_node()
      ->mutable_integer_literal()
      ->mutable_value()
      ->set_unsigned_decimal("42");

  const auto encoded = ctk::net::EventEncoder::encode(event);
  ASSERT_TRUE(encoded.has_match());
  EXPECT_EQ(encoded.match().bindings().at("literal").name(), "42");
  const auto &semantic =
      encoded.match().semantic_result().bindings().at("literal");
  ASSERT_TRUE(semantic.has_node());
  ASSERT_TRUE(semantic.node().has_integer_literal());
  EXPECT_EQ(semantic.node().integer_literal().value().unsigned_decimal(), "42");
}

struct FakeHandle : app::IQueryHandle {
  std::shared_ptr<app::IQueryEventSink> sink;
  std::atomic<bool> cancelled{false}, completed{false};
  void submit(app::QueryCommand command,
              std::function<void()> on_consumed = {}) override {
    app::QueryEvent event{app::EventKind::Control};
    event.request_id = command.request_id;
    event.action = "accepted";
    sink->publish(std::move(event));
    if (on_consumed)
      on_consumed();
  }
  void reject(std::string request_id, app::Outcome outcome,
              std::function<void()> on_consumed = {}) override {
    app::QueryEvent event{app::EventKind::Rejected};
    event.request_id = std::move(request_id);
    event.outcome = std::move(outcome);
    sink->publish(std::move(event));
    if (on_consumed)
      on_consumed();
  }
  void transport_done() override {}
  void close_input() override {
    if (completed.exchange(true))
      return;
    app::QueryEvent event{app::EventKind::Completed};
    sink->publish(std::move(event));
    sink->on_complete({});
  }
  void cancel() override {
    cancelled = true;
    if (!completed.exchange(true))
      sink->on_complete({app::OutcomeCode::Cancelled, "cancelled", {}});
  }
};
struct FakeController : app::IQueryController {
  std::shared_ptr<FakeHandle> task;
  std::jthread worker;
  int events = 300;
  std::shared_ptr<app::IQueryHandle>
  open(std::shared_ptr<app::IQueryEventSink> sink) override {
    task = std::make_shared<FakeHandle>();
    task->sink = std::move(sink);
    return task;
  }
  std::shared_ptr<app::IQueryHandle>
  start(app::QueryRequest,
        std::shared_ptr<app::IQueryEventSink> sink) override {
    auto handle = std::static_pointer_cast<FakeHandle>(open(sink));
    worker = std::jthread([handle, total = events] {
      for (int index = 0; index < total && !handle->cancelled; ++index) {
        app::QueryEvent event{app::EventKind::Match};
        event.file = "fixture.cpp";
        event.profile = "profile";
        event.bindings.emplace(
            "value",
            app::SemanticBinding{"VarDecl", std::to_string(index), "int"});
        if (!handle->sink->publish(std::move(event)))
          break;
      }
      if (!handle->completed.exchange(true)) {
        app::QueryEvent event{app::EventKind::Completed};
        event.match_count = total;
        handle->sink->publish(std::move(event));
        handle->sink->on_complete({});
      }
    });
    return handle;
  }
  void stop_admission() override {}
};
class SlowEngine final : public ctk::clang_layer::IQueryEngine {
public:
  ctk::clang_layer::QueryResult match(const ctk::clang_layer::FileInput &,
                                      const std::string &,
                                      const Checkpoint &checkpoint,
                                      const MatchCallback &on_match) override {
    for (int index = 0; index < 500; ++index) {
      if (!checkpoint()) {
        cancelled = true;
        return {false, true, false, "fake", "cancelled", 0};
      }
      on_match({{"value", {"VarDecl", "marker", "int"}}});
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    return {true, false, false, "fake", "", 0};
  }
  std::atomic<bool> cancelled{false};
};
ctk::config::Settings isolated_settings() {
  static std::atomic<int> number{0};
  ctk::config::Settings settings;
  // Small absolute paths avoid platform sockaddr_un pathname limits.
  settings.endpoint =
      "unix:///tmp/ctk-net-test-" +
      std::to_string(
          std::chrono::steady_clock::now().time_since_epoch().count()) +
      "-" + std::to_string(number++) + ".sock";
  return settings;
}
TEST(OutboundEventQueue, OverflowPreservesOrderAcrossMemoryAndDisk) {
  ctk::net::OutboundEventQueue queue;
  for (int i = 0; i < 300; ++i)
    queue.enqueue(std::to_string(i));
  for (int i = 0; i < 300; ++i)
    EXPECT_EQ(queue.take_next(), std::to_string(i));
  EXPECT_TRUE(queue.empty());
  queue.enqueue("after drain");
  EXPECT_EQ(queue.take_next(), "after drain");
}
TEST(OutboundEventQueue, BoundsIndividualMessages) {
  ctk::net::OutboundEventQueue queue;
  EXPECT_THROW(queue.enqueue(std::string(
                   ctk::net::OutboundEventQueue::max_event_bytes + 1, 'x')),
               std::runtime_error);
  EXPECT_TRUE(queue.empty());
}
TEST(NetworkTransport, CallbackStreamDrainsOverflowBeforeSuccessfulFinish) {
  FakeController controller;
  auto settings = isolated_settings();
  ctk::net::GrpcServerHost host(settings, controller);
  host.start();
  auto stub = wire::QueryService::NewStub(grpc::CreateChannel(
      settings.endpoint, grpc::InsecureChannelCredentials()));
  grpc::ClientContext context;
  context.set_deadline(std::chrono::system_clock::now() +
                       std::chrono::seconds(10));
  wire::QueryRequest request;
  request.set_query("varDecl()");
  auto reader = stub->Query(&context, request);
  wire::QueryEvent event;
  int matches = 0;
  bool completed = false;
  while (reader->Read(&event)) {
    EXPECT_FALSE(completed);
    if (event.has_match()) {
      EXPECT_EQ(event.match().file(), "fixture.cpp");
      EXPECT_EQ(event.match().bindings().at("value").name(),
                std::to_string(matches++));
    } else if (event.has_completed()) {
      completed = true;
      EXPECT_EQ(event.completed().match_count(), 300);
    }
  }
  EXPECT_TRUE(reader->Finish().ok());
  EXPECT_EQ(matches, 300);
  EXPECT_TRUE(completed);
  // A producer retaining the domain sink cannot call a cleaned-up reactor.
  EXPECT_FALSE(
      controller.task->sink->publish(app::QueryEvent{app::EventKind::Match}));
  host.shutdown();
}
TEST(NetworkTransport, BidiRejectsMalformedCommandAndCompletesAfterHalfClose) {
  FakeController controller;
  auto settings = isolated_settings();
  ctk::net::GrpcServerHost host(settings, controller);
  host.start();
  auto stub = wire::QueryService::NewStub(grpc::CreateChannel(
      settings.endpoint, grpc::InsecureChannelCredentials()));
  grpc::ClientContext context;
  context.set_deadline(std::chrono::system_clock::now() +
                       std::chrono::seconds(10));
  auto stream = stub->QuerySession(&context);
  wire::QueryCommand bad;
  bad.set_request_id("bad");
  ASSERT_TRUE(stream->Write(bad));
  wire::QueryCommand good;
  good.set_request_id("good");
  good.mutable_start_query()->set_query("varDecl()");
  ASSERT_TRUE(stream->Write(good));
  ASSERT_TRUE(stream->WritesDone());
  wire::QueryEvent event;
  bool rejected = false, accepted = false, completed = false;
  while (stream->Read(&event)) {
    if (event.has_rejected()) {
      rejected = true;
      EXPECT_EQ(event.request_id(), "bad");
    }
    if (event.has_control()) {
      accepted = true;
      EXPECT_EQ(event.request_id(), "good");
    }
    if (event.has_completed())
      completed = true;
  }
  EXPECT_TRUE(stream->Finish().ok());
  EXPECT_TRUE(rejected);
  EXPECT_TRUE(accepted);
  EXPECT_TRUE(completed);
  host.shutdown();
}
TEST(NetworkTransport, InitialLimitFailureCarriesStructuredDetails) {
  app::Outcome outcome{app::OutcomeCode::ResourceExhausted,
                       "admission rejected",
                       {{"session.max_files", 100, 100, 1, 101},
                        {"session.overhead_memory_bytes", 2147483648ULL,
                         2147483648ULL, 1, 2147483649ULL}}};
  auto status = ctk::net::GrpcStatusMapper::map(outcome);
  EXPECT_EQ(status.error_code(), grpc::StatusCode::RESOURCE_EXHAUSTED);
  wire::Rejected details;
  ASSERT_TRUE(details.ParseFromString(status.error_details()));
  ASSERT_EQ(details.violations_size(), 2);
  EXPECT_EQ(details.violations(1).limit_name(),
            "session.overhead_memory_bytes");
  EXPECT_EQ(details.violations(1).current_value(), 2147483648ULL);
}
TEST(NetworkTransport, DuplicateUnixListenerIsRejectedWithoutReplacingSocket) {
  FakeController first, second;
  auto settings = isolated_settings();
  ctk::net::GrpcServerHost owner(settings, first), contender(settings, second);
  owner.start();
  EXPECT_THROW(contender.start(), std::runtime_error);
  auto stub = wire::QueryService::NewStub(grpc::CreateChannel(
      settings.endpoint, grpc::InsecureChannelCredentials()));
  grpc::ClientContext context;
  context.set_deadline(std::chrono::system_clock::now() +
                       std::chrono::seconds(5));
  wire::QueryRequest request;
  request.set_query("varDecl()");
  auto reader = stub->Query(&context, request);
  wire::QueryEvent event;
  while (reader->Read(&event)) {
  }
  EXPECT_TRUE(reader->Finish().ok());
  owner.shutdown();
  EXPECT_NO_THROW(contender.start());
  contender.shutdown();
}
TEST(NetworkTransport,
     CancellationStopsAcceptedBatchAndReleasesReactorBeforeShutdown) {
  auto engine = std::make_shared<SlowEngine>();
  app::QueryController controller({}, engine);
  auto settings = isolated_settings();
  settings.shutdown_grace_ms = 200;
  ctk::net::GrpcServerHost host(settings, controller);
  host.start();
  auto stub = wire::QueryService::NewStub(grpc::CreateChannel(
      settings.endpoint, grpc::InsecureChannelCredentials()));
  grpc::ClientContext context;
  context.set_deadline(std::chrono::system_clock::now() +
                       std::chrono::seconds(5));
  wire::QueryRequest request;
  request.set_query("varDecl()");
  for (int index = 0; index < 8; ++index) {
    auto *file = request.add_files();
    file->set_path("/tmp/file-" + std::to_string(index) + ".cpp");
    file->set_working_directory("/tmp");
  }
  auto reader = stub->Query(&context, request);
  wire::QueryEvent event;
  while (reader->Read(&event) && !event.has_match()) {
  }
  ASSERT_TRUE(event.has_match());
  context.TryCancel();
  while (reader->Read(&event)) {
  }
  EXPECT_EQ(reader->Finish().error_code(), grpc::StatusCode::CANCELLED);
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(2);
  while (!engine->cancelled && std::chrono::steady_clock::now() < deadline)
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  EXPECT_TRUE(engine->cancelled);
  host.shutdown();
}
TEST(NetworkTransport, ShutdownDrainsAcceptedSessionWithoutClientHalfClose) {
  auto engine = std::make_shared<SlowEngine>();
  app::QueryController controller({}, engine);
  auto settings = isolated_settings();
  settings.shutdown_grace_ms = 5000;
  ctk::net::GrpcServerHost host(settings, controller);
  host.start();
  auto stub = wire::QueryService::NewStub(grpc::CreateChannel(
      settings.endpoint, grpc::InsecureChannelCredentials()));
  grpc::ClientContext context;
  context.set_deadline(std::chrono::system_clock::now() +
                       std::chrono::seconds(10));
  auto stream = stub->QuerySession(&context);
  wire::QueryCommand start;
  start.mutable_start_query()->set_query("varDecl()");
  ASSERT_TRUE(stream->Write(start));
  wire::QueryCommand add;
  auto *file = add.mutable_add_files()->add_files();
  file->set_path("/tmp/shutdown.cpp");
  file->set_working_directory("/tmp");
  ASSERT_TRUE(stream->Write(add));
  wire::QueryCommand match;
  match.mutable_match();
  ASSERT_TRUE(stream->Write(match));
  wire::QueryEvent event;
  while (stream->Read(&event) && !event.has_match()) {
  }
  ASSERT_TRUE(event.has_match());
  auto shutdown = std::async(std::launch::async, [&host] { host.shutdown(); });
  int matches = 1;
  bool completed = false;
  while (stream->Read(&event)) {
    if (event.has_match())
      ++matches;
    if (event.has_completed())
      completed = true;
  }
  EXPECT_TRUE(stream->Finish().ok());
  EXPECT_TRUE(completed);
  EXPECT_EQ(matches, 500);
  EXPECT_FALSE(engine->cancelled);
  EXPECT_EQ(shutdown.wait_for(std::chrono::seconds(1)),
            std::future_status::ready);
  shutdown.get();
}
} // namespace
