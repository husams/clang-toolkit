#include "repl_cancellation.hpp"

#include <atomic>
#include <cerrno>
#include <csignal>
#include <unistd.h>

#include <llvm/ADT/ScopeExit.h>

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

bool interactive_terminal() {
  return ::isatty(STDIN_FILENO) && ::isatty(STDOUT_FILENO);
}

llvm::Error with_prompt_interrupts(llvm::function_ref<llvm::Error()> run) {
  struct sigaction action {}, previous {};
  action.sa_handler = cancel;
  sigemptyset(&action.sa_mask);
  if (::sigaction(SIGINT, &action, &previous) != 0)
    return llvm::errorCodeToError(std::error_code(errno, std::generic_category()));
  auto restore = llvm::make_scope_exit([&] { ::sigaction(SIGINT, &previous, nullptr); });
  return run();
}

} // namespace ctk::jit
