#pragma once
#include <atomic>
#include <cstdio>
#include <deque>
#include <mutex>
#include <string>

namespace ctk::net {
// A bounded memory FIFO with an ordered disk overflow. Spooling is application
// I/O, not a wait for a client to free network capacity. No matches are
// dropped. Reads run on the delivery dispatcher, never in a gRPC reaction.
class OutboundEventQueue {
public:
  static constexpr std::size_t memory_capacity = 64;
  static constexpr std::size_t max_event_bytes = 512 * 1024;
  ~OutboundEventQueue();
  void enqueue(std::string bytes);
  std::string take_next();
  bool empty() const { return count_.load() == 0; }

private:
  std::mutex mutex_;
  std::deque<std::string> memory_;
  std::FILE *spool_{};
  long read_offset_{}, write_offset_{};
  std::size_t disk_count_{};
  std::atomic<std::size_t> count_{};
};
} // namespace ctk::net
