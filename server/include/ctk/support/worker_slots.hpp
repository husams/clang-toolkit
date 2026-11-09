#pragma once

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <mutex>

namespace ctk::compat {

class WorkerSlots {
public:
  explicit WorkerSlots(std::size_t count)
      : available_(count) {}

  template <class Rep, class Period>
  bool try_acquire_for(std::chrono::duration<Rep, Period> timeout) {
    std::unique_lock lock(mutex_);
    if (!ready_.wait_for(lock, timeout, [&] { return available_ > 0; })) {
      return false;
    }
    --available_;
    return true;
  }

  void release() {
    {
      std::lock_guard lock(mutex_);
      ++available_;
    }
    ready_.notify_one();
  }

private:
  std::mutex mutex_;
  std::condition_variable ready_;
  std::size_t available_;
};

} // namespace ctk::compat
