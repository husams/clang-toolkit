#pragma once
#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace ctk::clang_layer {
class IQueryEngine;
}

namespace ctk::application {
struct FileInput {
  std::string path;
  std::vector<std::string> compile_arguments;
  std::string working_directory;
};
struct QueryRequest {
  std::string query;
  std::vector<FileInput> files;
};
enum class CommandKind { StartQuery, AddFiles, Match, Pause, Resume };
struct QueryCommand {
  std::string request_id;
  CommandKind kind;
  std::string query;
  std::vector<FileInput> files;
};
struct LimitViolation {
  std::string limit_name;
  std::uint64_t current_value{}, configured_limit{}, requested_increment{},
      projected_value{};
};
enum class OutcomeCode {
  Ok,
  InvalidArgument,
  ResourceExhausted,
  NotFound,
  Internal,
  Cancelled,
  FailedPrecondition
};
struct Outcome {
  OutcomeCode code{OutcomeCode::Ok};
  std::string message;
  std::vector<LimitViolation> violations;
};
struct SemanticBinding {
  std::string kind, name, type;
};
enum class EventKind {
  Queued,
  Started,
  Progress,
  Match,
  Completed,
  Rejected,
  Control
};
struct QueryEvent {
  EventKind kind;
  std::string request_id, file, profile, action;
  std::uint64_t completed_files{}, accepted_files{}, match_count{},
      pending_requests{};
  std::map<std::string, SemanticBinding> bindings;
  Outcome outcome;
};
class CancellationSource {
public:
  void cancel() {
    {
      std::lock_guard lock(mutex_);
      cancelled_.store(true);
    }
    cv_.notify_all();
  }
  bool cancelled() const { return cancelled_.load(); }
  void pause(bool value) {
    {
      std::lock_guard lock(mutex_);
      paused_.store(value);
    }
    cv_.notify_all();
  }
  bool checkpoint() {
    std::unique_lock lock(mutex_);
    cv_.wait(lock, [&] { return cancelled() || !paused_.load(); });
    return !cancelled();
  }

private:
  std::atomic<bool> cancelled_{false}, paused_{false};
  std::mutex mutex_;
  std::condition_variable cv_;
};
class IQueryEventSink {
public:
  virtual ~IQueryEventSink() = default;
  // Publication must not wait for network capacity. false means cancelled.
  virtual bool publish(QueryEvent event) = 0;
  virtual void on_complete(Outcome outcome) = 0;
};
class IQueryHandle {
public:
  virtual ~IQueryHandle() = default;
  virtual void submit(QueryCommand command,
                      std::function<void()> on_consumed = {}) = 0;
  virtual void close_input() = 0;
  virtual void cancel() = 0;
  virtual void reject(std::string request_id, Outcome outcome,
                      std::function<void()> on_consumed = {}) = 0;
  virtual void transport_done() = 0;
};
class IQueryController {
public:
  virtual ~IQueryController() = default;
  virtual std::shared_ptr<IQueryHandle>
  start(QueryRequest request, std::shared_ptr<IQueryEventSink> sink) = 0;
  virtual std::shared_ptr<IQueryHandle>
  open(std::shared_ptr<IQueryEventSink> sink) = 0;
  virtual void stop_admission() = 0;
};
struct ControllerSettings {
  std::size_t workers{3}, pending_requests{100}, max_files{100};
  std::uint64_t max_memory_bytes{2147483648ULL},
      overhead_memory_bytes{2147483648ULL};
};
class QueryController final : public IQueryController {
public:
  struct Impl;
  explicit QueryController(ControllerSettings settings = {});
  QueryController(ControllerSettings settings,
                  std::shared_ptr<ctk::clang_layer::IQueryEngine> engine);
  ~QueryController();
  std::shared_ptr<IQueryHandle>
      start(QueryRequest, std::shared_ptr<IQueryEventSink>) override;
  std::shared_ptr<IQueryHandle> open(std::shared_ptr<IQueryEventSink>) override;
  void stop_admission() override;

private:
  std::shared_ptr<Impl> impl_;
};
} // namespace ctk::application
