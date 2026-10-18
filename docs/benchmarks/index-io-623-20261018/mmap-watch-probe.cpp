#include "ctk/platform/file_watch.hpp"
#include <chrono>
#include <filesystem>
#include <fcntl.h>
#include <iostream>
#include <string>
#include <sys/mman.h>
#include <thread>
#include <unistd.h>

int main() {
  for (bool sync : {false, true}) {
    auto path = std::filesystem::path("/tmp") /
        (std::string("ctk-filewatch-mmap-") + (sync ? "sync" : "nosync") + "-" + std::to_string(getpid()));
    int fd = open(path.c_str(), O_RDWR | O_CREAT | O_TRUNC, 0600);
    if (fd < 0 || ftruncate(fd, 4096) != 0) return 2;
    auto *bytes = static_cast<volatile char *>(mmap(nullptr, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0));
    if (bytes == MAP_FAILED) return 3;
    bytes[0] = 'A'; // dirty the page before the watcher starts
    ctk::platform::FileWatch watcher(8);
    if (!watcher.add(path)) return 4;
    const auto before = ctk::platform::FileWatch::identity(path);
    bytes[1] = 'B'; // modify an already-dirty mapped page after the watcher starts
    if (sync && msync(const_cast<char *>(bytes), 4096, MS_SYNC) != 0) return 5;
    bool event = false;
    for (int i = 0; i != 50; ++i) {
      event |= watcher.changed();
      std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    const auto after = ctk::platform::FileWatch::identity(path);
    std::cout << (sync ? "msync" : "no-msync") << " event=" << event
              << " identity_unchanged=" << (before && after && *before == *after)
              << " bytes=" << bytes[0] << bytes[1] << "\n";
    munmap(const_cast<char *>(bytes), 4096);
    close(fd);
    std::filesystem::remove(path);
  }
}
