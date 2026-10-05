#include "ctk/net/outbound_event_queue.hpp"
#include <cstdint>
#include <stdexcept>

namespace ctk::net {
OutboundEventQueue::~OutboundEventQueue() {
  if (spool_)
    std::fclose(spool_);
}
void OutboundEventQueue::enqueue(std::string bytes) {
  if (bytes.size() > max_event_bytes)
    throw std::runtime_error("query event exceeds the 512 KiB event limit");
  std::lock_guard lock(mutex_);
  if (!disk_count_ && memory_.size() < memory_capacity) {
    memory_.push_back(std::move(bytes));
  } else {
    if (!spool_)
      spool_ = std::tmpfile();
    if (!spool_)
      throw std::runtime_error("cannot create query event spool");
    auto length = static_cast<std::uint32_t>(bytes.size());
    if (std::fseek(spool_, write_offset_, SEEK_SET) ||
        std::fwrite(&length, sizeof(length), 1, spool_) != 1 ||
        std::fwrite(bytes.data(), 1, bytes.size(), spool_) != bytes.size())
      throw std::runtime_error("cannot spool query event");
    write_offset_ = std::ftell(spool_);
    if (write_offset_ < 0)
      throw std::runtime_error("cannot locate query event spool");
    ++disk_count_;
  }
  ++count_;
}
std::string OutboundEventQueue::take_next() {
  std::lock_guard lock(mutex_);
  std::string result;
  if (!memory_.empty()) {
    result = std::move(memory_.front());
    memory_.pop_front();
  } else if (disk_count_) {
    std::uint32_t length{};
    if (std::fseek(spool_, read_offset_, SEEK_SET) ||
        std::fread(&length, sizeof(length), 1, spool_) != 1 ||
        length > max_event_bytes)
      throw std::runtime_error("cannot read query event spool");
    result.resize(length);
    if (std::fread(result.data(), 1, length, spool_) != length)
      throw std::runtime_error("incomplete query event spool");
    read_offset_ = std::ftell(spool_);
    --disk_count_;
    if (!disk_count_)
      read_offset_ = write_offset_ = 0;
  } else {
    throw std::logic_error("empty outbound queue");
  }
  --count_;
  return result;
}
} // namespace ctk::net
