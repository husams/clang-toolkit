#pragma once
#include "ctk/net/outbound_event_queue.hpp"
#include "ctk/net/protocol_adapter.hpp"
#include "ctk/net/stream_write_pump.hpp"
#include <condition_variable>
#include <functional>
#include <optional>

namespace ctk::net {
// Shared state outlives transport detachment. Producers hold this object, never
// a reactor. The same mutex serializes every operation with Finish and detach.
class QueryCallState : public std::enable_shared_from_this<QueryCallState> {
public:
  using Write = std::function<void(const query::v1::QueryEvent *)>;
  using Finish = std::function<void(grpc::Status)>;
  static std::shared_ptr<QueryCallState> create();
  void attach(Write write, Finish finish);
  void set_handle(std::shared_ptr<application::IQueryHandle>);
  bool publish(application::QueryEvent);
  void complete(application::Outcome);
  void write_completed(bool ok);
  void request_cancel();
  void detach_transport();
  void read_next(const std::function<void()> &);
  std::shared_ptr<application::IQueryHandle> handle();

private:
  void run();
  void fail_delivery(std::string message);
  std::mutex mutex_;
  std::condition_variable changed_;
  OutboundEventQueue outbound_;
  // Payload is immutable until OnWriteDone releases it.
  StreamWritePump pump_;
  std::optional<application::Outcome> terminal_, delivery_failure_;
  Write write_;
  Finish finish_;
  std::shared_ptr<application::IQueryHandle> handle_;
  bool detached_{false}, cancelled_{false};
};
class RpcEventSink final : public application::IQueryEventSink {
public:
  explicit RpcEventSink(std::shared_ptr<QueryCallState> state)
      : state_(std::move(state)) {}
  bool publish(application::QueryEvent event) override {
    return state_->publish(std::move(event));
  }
  void on_complete(application::Outcome outcome) override {
    state_->complete(std::move(outcome));
  }

private:
  std::shared_ptr<QueryCallState> state_;
};
} // namespace ctk::net
