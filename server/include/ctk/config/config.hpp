#pragma once

#include <cstdint>
#include <filesystem>
#include <map>
#include <optional>
#include <string>
#include <variant>

namespace ctk::config {

struct GrpcSettings {
  std::optional<int> max_receive_message_bytes;
  std::optional<int> max_send_message_bytes;
};

using ConfigValue = std::variant<std::monostate, std::string, std::int64_t>;

struct Settings {
  std::string endpoint;
  int pool_size{3};
  int queue_size{100};
  int max_files{100};
  std::int64_t max_memory_bytes{2147483648};
  GrpcSettings server_grpc{std::nullopt, -1};
  GrpcSettings client_grpc{-1, std::nullopt};
  std::optional<std::int64_t> rpc_timeout_ms;
  std::optional<std::int64_t> shutdown_grace_ms;
  // Flattened merged scalar values, including defaults and explicit nulls.
  // Socket values retain their supplied spelling; endpoint is fully resolved.
  std::map<std::string, ConfigValue> effective_values;
  std::map<std::string, std::string> provenance;
};

// Loads and validates every discovered layer, then resolves the winning
// endpoint. Empty home uses $HOME; paths can be injected to make discovery
// deterministic.
Settings load(std::optional<std::filesystem::path> cli_file = std::nullopt,
              std::filesystem::path cwd = std::filesystem::current_path(),
              std::optional<std::filesystem::path> home = std::nullopt,
              std::filesystem::path system_directory = "/etc/clang-toolkit");

} // namespace ctk::config
