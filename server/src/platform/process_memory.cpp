#include "ctk/platform/process_memory.hpp"
#if defined(__APPLE__)
#include <mach/mach.h>
#elif defined(__linux__)
#include <fstream>
#include <unistd.h>
#endif

namespace ctk::platform {
std::optional<std::uint64_t> resident_memory_bytes() {
#if defined(__APPLE__)
  mach_task_basic_info_data_t info{};
  mach_msg_type_number_t count = MACH_TASK_BASIC_INFO_COUNT;
  if (task_info(mach_task_self(), MACH_TASK_BASIC_INFO,
                reinterpret_cast<task_info_t>(&info), &count) == KERN_SUCCESS)
    return info.resident_size;
#elif defined(__linux__)
  std::ifstream input("/proc/self/statm");
  std::uint64_t pages{}, resident{};
  const auto page_size = sysconf(_SC_PAGESIZE);
  if (page_size > 0 && input >> pages >> resident)
    return resident * static_cast<std::uint64_t>(page_size);
#endif
  return std::nullopt;
}
}
