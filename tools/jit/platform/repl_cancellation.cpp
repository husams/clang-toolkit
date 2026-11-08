#include "repl_cancellation.hpp"

#include <atomic>
#include <csignal>

namespace ctk::jit {
namespace {

std::atomic<bool> cancelled{false};
static_assert(decltype(cancelled)::is_always_lock_free);

void cancel(int) {
  request_repl_cancellation();
}

} // namespace

void install_repl_cancellation() {
  std::signal(SIGUSR1, cancel);
}

void request_repl_cancellation() {
  cancelled.store(true, std::memory_order_relaxed);
}

void clear_repl_cancellation() {
  cancelled.store(false, std::memory_order_relaxed);
}

bool repl_cancelled() {
  return cancelled.load(std::memory_order_relaxed);
}

} // namespace ctk::jit
