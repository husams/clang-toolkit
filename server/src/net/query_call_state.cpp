#include "ctk/net/query_call_state.hpp"
#include <thread>

namespace ctk::net {
std::shared_ptr<QueryCallState> QueryCallState::create() {
  auto state = std::make_shared<QueryCallState>();
  // This dispatcher only drains event storage and starts transport operations;
  // parsing and matching are restricted to the application worker pool.
  std::thread([state] { state->run(); }).detach();
  return state;
}
void QueryCallState::attach(Write write, Finish finish) {
  std::lock_guard lock(mutex_);
  write_ = std::move(write);
  finish_ = std::move(finish);
  changed_.notify_one();
}
void QueryCallState::set_handle(
    std::shared_ptr<application::IQueryHandle> handle) {
  bool cancelled;
  {
    std::lock_guard lock(mutex_);
    handle_ = handle;
    cancelled = cancelled_;
  }
  if (cancelled && handle)
    handle->cancel();
}
std::shared_ptr<application::IQueryHandle> QueryCallState::handle() {
  std::lock_guard lock(mutex_);
  return handle_;
}
bool QueryCallState::publish(application::QueryEvent event) {
  {
    std::lock_guard lock(mutex_);
    if (detached_ || pump_.finishing() || cancelled_ || terminal_)
      return false;
  }
  try {
    outbound_.enqueue(EventEncoder::encode(event).SerializeAsString());
  } catch (const std::exception &error) {
    fail_delivery(error.what());
    return false;
  }
  changed_.notify_one();
  return true;
}
void QueryCallState::complete(application::Outcome outcome) {
  std::lock_guard lock(mutex_);
  if (!terminal_)
    terminal_ = std::move(outcome);
  changed_.notify_one();
}
void QueryCallState::request_cancel() {
  std::shared_ptr<application::IQueryHandle> task;
  {
    std::lock_guard lock(mutex_);
    cancelled_ = true;
    task = handle_;
    changed_.notify_one();
  }
  if (task)
    task->cancel();
}
void QueryCallState::fail_delivery(std::string message) {
  {
    std::lock_guard lock(mutex_);
    delivery_failure_ = application::Outcome{
        application::OutcomeCode::Internal, std::move(message), {}};
  }
  request_cancel();
}
void QueryCallState::write_completed(bool ok) {
  {
    std::lock_guard lock(mutex_);
    if (!ok)
      cancelled_ = true;
    pump_.write_completed();
    changed_.notify_one();
  }
  if (!ok)
    request_cancel();
}
void QueryCallState::read_next(const std::function<void()> &read) {
  std::lock_guard lock(mutex_);
  if (!detached_ && !pump_.finishing() && !cancelled_)
    read();
}
void QueryCallState::detach_transport() {
  std::shared_ptr<application::IQueryHandle> task;
  {
    std::lock_guard lock(mutex_);
    detached_ = true;
    write_ = {};
    finish_ = {};
    task = std::move(handle_);
    changed_.notify_one();
  }
  if (task)
    task->transport_done();
}
void QueryCallState::run() {
  for (;;) {
    std::unique_lock lock(mutex_);
    changed_.wait(lock, [&] {
      return detached_ ||
             (finish_ && !pump_.finishing() && !pump_.writing() &&
              (terminal_.has_value() || (!cancelled_ && !outbound_.empty())));
    });
    if (detached_)
      return;
    if ((cancelled_ || outbound_.empty()) && terminal_) {
      auto outcome = delivery_failure_.value_or(*terminal_);
      if (cancelled_ && !delivery_failure_)
        outcome = {application::OutcomeCode::Cancelled, "query cancelled", {}};
      pump_.begin_finish();
      finish_(GrpcStatusMapper::map(outcome));
      continue;
    }
    if (cancelled_)
      continue;
    lock.unlock();
    query::v1::QueryEvent next;
    try {
      if (!next.ParseFromString(outbound_.take_next()))
        throw std::runtime_error("invalid spooled query event");
    } catch (const std::exception &error) {
      fail_delivery(error.what());
      continue;
    }
    lock.lock();
    if (detached_ || pump_.finishing() || cancelled_)
      continue;
    write_(pump_.begin_write(std::move(next)));
  }
}
} // namespace ctk::net
