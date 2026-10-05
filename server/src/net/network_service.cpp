#include "ctk/net/network_service.hpp"
#include "ctk/net/query_call_state.hpp"
#include <stdexcept>

namespace ctk::net {
namespace {
class QueryStreamReactor final
    : public grpc::ServerWriteReactor<query::v1::QueryEvent> {
public:
  QueryStreamReactor(application::IQueryController &controller,
                     const query::v1::QueryRequest &request)
      : state_(QueryCallState::create()) {
    state_->attach([this](auto *event) { StartWrite(event); },
                   [this](auto status) { Finish(std::move(status)); });
    auto sink = std::make_shared<RpcEventSink>(state_);
    try {
      state_->set_handle(
          controller.start(RequestDecoder::decode_query(request), sink));
    } catch (const std::invalid_argument &error) {
      state_->complete(
          {application::OutcomeCode::InvalidArgument, error.what(), {}});
    } catch (const std::exception &error) {
      state_->complete({application::OutcomeCode::Internal, error.what(), {}});
    }
  }
  void OnWriteDone(bool ok) override { state_->write_completed(ok); }
  void OnCancel() override { state_->request_cancel(); }
  void OnDone() override {
    state_->detach_transport();
    delete this;
  }

private:
  std::shared_ptr<QueryCallState> state_;
};
class QuerySessionReactor final
    : public grpc::ServerBidiReactor<query::v1::QueryCommand,
                                     query::v1::QueryEvent> {
public:
  explicit QuerySessionReactor(application::IQueryController &controller)
      : state_(QueryCallState::create()) {
    state_->attach([this](auto *event) { StartWrite(event); },
                   [this](auto status) { Finish(std::move(status)); });
    try {
      state_->set_handle(
          controller.open(std::make_shared<RpcEventSink>(state_)));
      state_->read_next([this] { StartRead(&command_); });
    } catch (const std::exception &error) {
      state_->complete({application::OutcomeCode::Internal, error.what(), {}});
    }
  }
  void OnReadDone(bool ok) override {
    auto task = state_->handle();
    if (!task)
      return;
    if (!ok) {
      task->close_input();
      return;
    }
    // Keep only one decoded command alive per stream; accepted query work
    // continues independently while the control dispatcher consumes it.
    auto consumed = [state = state_, this] {
      state->read_next([this] { StartRead(&command_); });
    };
    try {
      task->submit(RequestDecoder::decode_command(command_), consumed);
    } catch (const std::exception &error) {
      task->reject(
          command_.request_id(),
          {application::OutcomeCode::InvalidArgument, error.what(), {}},
          consumed);
    }
  }
  void OnWriteDone(bool ok) override { state_->write_completed(ok); }
  void OnCancel() override { state_->request_cancel(); }
  void OnDone() override {
    state_->detach_transport();
    delete this;
  }

private:
  query::v1::QueryCommand command_;
  std::shared_ptr<QueryCallState> state_;
};
} // namespace
grpc::ServerWriteReactor<query::v1::QueryEvent> *
NetworkServiceAdapter::Query(grpc::CallbackServerContext *,
                             const query::v1::QueryRequest *request) {
  return new QueryStreamReactor(controller_, *request);
}
grpc::ServerBidiReactor<query::v1::QueryCommand, query::v1::QueryEvent> *
NetworkServiceAdapter::QuerySession(grpc::CallbackServerContext *) {
  return new QuerySessionReactor(controller_);
}
} // namespace ctk::net
