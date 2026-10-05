#pragma once

#include <condition_variable>
#include <cstddef>
#include <functional>
#include <mutex>
#include <queue>
#include <thread>
#include <utility>
#include <vector>

namespace ctk::application::detail {

// Bounded request-level worker queue. A queued AddFiles batch occupies one
// slot; running requests no longer count against the pending limit.
class QueryExecutor final {
public:
  QueryExecutor(std::size_t worker_count, std::size_t pending_limit)
      : pending_limit_(pending_limit == 0 ? 1 : pending_limit) {
    const auto count = worker_count == 0 ? 1 : worker_count;
    workers_.reserve(count);
    for (std::size_t i = 0; i < count; ++i) {
      workers_.emplace_back([this] { worker_loop(); });
    }
  }

  QueryExecutor(const QueryExecutor &) = delete;
  QueryExecutor &operator=(const QueryExecutor &) = delete;

  ~QueryExecutor() { shutdown(); }

  bool enqueue(std::function<void()> task) {
    std::lock_guard lock(mutex_);
    if (stopping_ || !accepting_ || tasks_.size() >= pending_limit_)
      return false;
    tasks_.push(std::move(task));
    condition_.notify_one();
    return true;
  }

  std::size_t pending_count() {
    std::lock_guard lock(mutex_);
    return tasks_.size();
  }

  void stop_admission() {
    std::lock_guard lock(mutex_);
    accepting_ = false;
  }

  void shutdown() {
    {
      std::lock_guard lock(mutex_);
      if (stopping_)
        return;
      accepting_ = false;
      stopping_ = true;
    }
    condition_.notify_all();
    for (auto &worker : workers_) {
      if (worker.joinable())
        worker.join();
    }
  }

private:
  void worker_loop() {
    for (;;) {
      std::function<void()> task;
      {
        std::unique_lock lock(mutex_);
        condition_.wait(lock, [&] { return stopping_ || !tasks_.empty(); });
        if (stopping_ && tasks_.empty())
          return;
        task = std::move(tasks_.front());
        tasks_.pop();
      }
      try {
        task();
      } catch (...) {
        // One failed request must not stop the worker pool.
      }
    }
  }

  std::size_t pending_limit_;
  std::mutex mutex_;
  std::condition_variable condition_;
  std::queue<std::function<void()>> tasks_;
  std::vector<std::thread> workers_;
  bool accepting_ = true;
  bool stopping_ = false;
};

} // namespace ctk::application::detail
