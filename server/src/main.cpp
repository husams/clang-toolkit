#include "ctk/net/server.hpp"
#include "ctk/version.hpp"
#include <chrono>
#include <csignal>
#include <iostream>
#include <optional>
#include <thread>

namespace {
volatile std::sig_atomic_t shutdown_requested = 0;
void request_shutdown(int) { shutdown_requested = 1; }
} // namespace

int main(int argc, char **argv) {
  try {
    std::optional<std::filesystem::path> selected;
    bool print_config = false;
    for (int index = 1; index < argc; ++index) {
      std::string argument(argv[index]);
      if (argument == "-c" || argument == "--cofing") {
        if (++index == argc)
          throw std::invalid_argument(argument + " requires a file pathname");
        selected = argv[index];
      } else if (argument == "--version") {
        std::cout << "ctk-server " << ctk::build::version << " (revision "
                  << ctk::build::revision << ")\n";
        return 0;
      } else if (argument == "--print-config")
        print_config = true;
      else if (argument == "--help" || argument == "-h") {
        std::cout << "ctk-server [-c FILE | --cofing FILE] [--print-config] "
                     "[--version]\n";
        return 0;
      } else
        throw std::invalid_argument("unknown option: " + argument);
    }
    auto settings = ctk::config::load(selected);
    if (print_config) {
      // Expose the resolved endpoint without imposing gRPC tuning defaults.
      std::cout << settings.endpoint << '\n';
      return 0;
    }
    ctk::application::ControllerSettings application;
    application.workers = settings.pool_size;
    application.pending_requests = settings.queue_size;
    application.max_files = settings.max_files;
    application.max_memory_bytes = settings.max_memory_bytes;
    ctk::application::QueryController controller(application);
    ctk::net::GrpcServerHost server(settings, controller);
    std::signal(SIGINT, request_shutdown);
    std::signal(SIGTERM, request_shutdown);
    server.start();
    std::cout << "ctk-server listening on " << server.endpoint() << std::endl;
    while (!shutdown_requested)
      std::this_thread::sleep_for(std::chrono::milliseconds(50));
    server.shutdown();
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "ctk-server: " << error.what() << '\n';
    return 1;
  }
}
