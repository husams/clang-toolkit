#include "ctk/config/config.hpp"

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <string>

namespace {

class ConfigTree {
public:
  ConfigTree() {
    root_ =
        std::filesystem::temp_directory_path() /
        ("ctk-config-test-" + std::to_string(static_cast<std::int64_t>(
                                  std::filesystem::file_time_type::clock::now()
                                      .time_since_epoch()
                                      .count())));
    std::filesystem::create_directories(root_);
  }
  ~ConfigTree() { std::filesystem::remove_all(root_); }
  std::filesystem::path dir(std::string name) {
    auto result = root_ / name;
    std::filesystem::create_directories(result);
    return result;
  }
  std::filesystem::path write(const std::filesystem::path &directory,
                              std::string name, std::string text) {
    auto path = directory / std::move(name);
    std::ofstream(path) << text;
    return path;
  }
  const std::filesystem::path &root() const { return root_; }

private:
  std::filesystem::path root_;
};

TEST(NetworkConfig, MergesEveryLayerAndResolvesRelativePathFromWinningFile) {
  ConfigTree files;
  const auto system = files.dir("system");
  const auto home = files.dir("home");
  const auto cwd = files.dir("project");
  const auto cli_dir = files.dir("selected");
  files.write(
      system, "clang-toolkit.yaml",
      "pool:\n  size: 4\nnetwork:\n  unix:\n    socket_path: system.sock\n");
  files.write(home, "clang-toolkit.yaml", "queue:\n  size: 20\n");
  files.write(home, ".clang-toolkit.yaml", "pool:\n  size: 5\n");
  files.write(cwd, "clang-toolkit.yaml", "session:\n  max_files: 7\n");
  files.write(cwd, ".clang-toolkit.yaml",
              "network:\n  unix:\n    socket_path: .ctk/run.sock\n");
  auto selected = files.write(cli_dir, "chosen.yaml", "queue:\n  size: 33\n");

  const auto settings = ctk::config::load(selected, cwd, home, system);

  EXPECT_EQ(settings.pool_size, 5);
  EXPECT_EQ(settings.queue_size, 33);
  EXPECT_EQ(settings.max_files, 7);
  EXPECT_EQ(settings.max_memory_bytes, 2147483648);
  EXPECT_EQ(settings.endpoint, "unix://" + (cwd / ".ctk/run.sock").string());
}

TEST(NetworkConfig, DefaultsToTemporaryUnixEndpointAndKeepsGrpcUnset) {
  ConfigTree files;
  const auto cwd = files.dir("empty");
  const auto settings =
      ctk::config::load(std::nullopt, cwd, files.dir("home"), files.dir("etc"));
  EXPECT_EQ(settings.endpoint,
            "unix://" +
                (std::filesystem::temp_directory_path() / "ctk.sock").string());
  EXPECT_EQ(settings.pool_size, 3);
  EXPECT_EQ(settings.queue_size, 100);
  EXPECT_FALSE(settings.server_grpc.max_receive_message_bytes);
  EXPECT_FALSE(settings.client_grpc.max_send_message_bytes);
  EXPECT_FALSE(settings.rpc_timeout_ms);
  EXPECT_FALSE(settings.shutdown_grace_ms);
}

TEST(NetworkConfig, RequiresLoopbackTcpHostAndPortAndFormatsIpv6) {
  ConfigTree files;
  const auto cwd = files.dir("project");
  auto path = files.write(
      cwd, "clang-toolkit.yaml",
      "network:\n  transport: tcp\n  tcp:\n    host: ::1\n    port: 50051\n");
  const auto settings =
      ctk::config::load(std::nullopt, cwd, files.dir("home"), files.dir("etc"));
  EXPECT_EQ(settings.endpoint, "[::1]:50051");
  EXPECT_NO_THROW(ctk::config::load(path, files.dir("other"),
                                    files.dir("home2"), files.dir("etc2")));
}

TEST(NetworkConfig, RejectsUnknownDuplicateAndInvalidOverriddenValues) {
  ConfigTree files;
  const auto system = files.dir("system");
  const auto cwd = files.dir("project");
  files.write(system, "clang-toolkit.yaml", "pool:\n  size: 0\n");
  files.write(cwd, "clang-toolkit.yaml", "pool:\n  size: 8\n");
  EXPECT_THROW(ctk::config::load(std::nullopt, cwd, files.dir("home"), system),
               std::runtime_error);

  const auto duplicate = files.write(files.dir("duplicate"), "bad.yaml",
                                     "pool:\n  size: 2\n  size: 3\n");
  EXPECT_THROW(ctk::config::load(duplicate, files.dir("elsewhere"),
                                 files.dir("h2"), files.dir("e2")),
               std::runtime_error);

  const auto unknown = files.write(files.dir("unknown"), "bad.yaml",
                                   "pool:\n  size: 2\n  future_option: 1\n");
  EXPECT_THROW(ctk::config::load(unknown, files.dir("elsewhere2"),
                                 files.dir("h3"), files.dir("e3")),
               std::runtime_error);
}

TEST(NetworkConfig, ValidatesInactiveBranchTypesAndTcpLoopbackRestriction) {
  ConfigTree files;
  const auto cwd = files.dir("project");
  auto bad_inactive = files.write(
      cwd, "clang-toolkit.yaml",
      "network:\n  transport: unix\n  tcp:\n    port: not-a-number\n");
  EXPECT_THROW(ctk::config::load(bad_inactive, files.dir("other"),
                                 files.dir("home"), files.dir("etc")),
               std::runtime_error);

  auto remote = files.write(files.dir("remote"), "config.yaml",
                            "network:\n  transport: tcp\n  tcp:\n    host: "
                            "192.168.1.8\n    port: 50051\n");
  EXPECT_THROW(ctk::config::load(remote, files.dir("elsewhere"),
                                 files.dir("home2"), files.dir("etc2")),
               std::runtime_error);

  auto missing =
      files.write(files.dir("missing"), "config.yaml",
                  "network:\n  transport: tcp\n  tcp:\n    host: 127.0.0.1\n");
  EXPECT_THROW(ctk::config::load(missing, files.dir("elsewhere2"),
                                 files.dir("home3"), files.dir("etc3")),
               std::runtime_error);
}

TEST(NetworkConfig, OptionalGrpcValuesCanBeClearedAndRespectRanges) {
  ConfigTree files;
  const auto system = files.dir("system");
  const auto cli_dir = files.dir("cli");
  files.write(system, "clang-toolkit.yaml",
              "server:\n  grpc:\n    max_send_message_bytes: 1024\nclient:\n  "
              "rpc_timeout_ms: 50\n");
  auto cli = files.write(
      cli_dir, "config.yaml",
      "server:\n  shutdown_grace_ms: 0\n  grpc:\n    max_send_message_bytes: "
      "null\n    max_receive_message_bytes: -1\nclient:\n  rpc_timeout_ms: "
      "null\n  grpc:\n    max_receive_message_bytes: 4096\n");
  const auto settings =
      ctk::config::load(cli, files.dir("cwd"), files.dir("home"), system);
  EXPECT_FALSE(settings.server_grpc.max_send_message_bytes);
  EXPECT_EQ(settings.server_grpc.max_receive_message_bytes, -1);
  EXPECT_EQ(settings.client_grpc.max_receive_message_bytes, 4096);
  EXPECT_FALSE(settings.rpc_timeout_ms);
  EXPECT_EQ(settings.shutdown_grace_ms, 0);
}

TEST(NetworkConfig, ExplicitMissingFileIsAnError) {
  ConfigTree files;
  EXPECT_THROW(ctk::config::load(files.root() / "missing.yaml", files.root(),
                                 files.root(), files.root()),
               std::runtime_error);
}

TEST(NetworkConfig,
     RejectsInvalidTransportAndTcpPortEvenWhenOverriddenOrInactive) {
  ConfigTree files;
  const auto system = files.dir("system");
  const auto cli_dir = files.dir("cli");
  files.write(system, "clang-toolkit.yaml", "network:\n  transport: udp\n");
  auto cli =
      files.write(cli_dir, "config.yaml", "network:\n  transport: unix\n");
  EXPECT_THROW(
      ctk::config::load(cli, files.dir("cwd"), files.dir("home"), system),
      std::runtime_error);

  auto bad_port = files.write(files.dir("inactive"), "config.yaml",
                              "network:\n  transport: unix\n  tcp:\n    host: "
                              "127.0.0.1\n    port: 70000\n");
  EXPECT_THROW(ctk::config::load(bad_port, files.dir("other"), files.dir("h2"),
                                 files.dir("s2")),
               std::runtime_error);
}

TEST(NetworkConfig, RejectsNulScalarsUnsupportedTagsAndRecursiveAliases) {
  ConfigTree files;
  const auto cwd = files.dir("cwd");
  auto nul_path =
      files.write(cwd, "nul-path.yaml",
                  "network:\n  unix:\n    socket_path: \"sock\\0name\"\n");
  EXPECT_THROW(ctk::config::load(nul_path, files.dir("other"),
                                 files.dir("home"), files.dir("etc")),
               std::runtime_error);

  auto nul_host = files.write(files.dir("nul-host"), "config.yaml",
                              "network:\n  transport: tcp\n  tcp:\n    host: "
                              "\"127.0.0.1\\0.evil\"\n    port: 50051\n");
  EXPECT_THROW(ctk::config::load(nul_host, files.dir("other2"), files.dir("h2"),
                                 files.dir("e2")),
               std::runtime_error);

  auto tagged =
      files.write(files.dir("tagged"), "config.yaml",
                  "network:\n  unix:\n    socket_path: !custom path\n");
  EXPECT_THROW(ctk::config::load(tagged, files.dir("other3"), files.dir("h3"),
                                 files.dir("e3")),
               std::runtime_error);

  auto recursive = files.write(files.dir("recursive"), "config.yaml",
                               "network: &network\n  unix: *network\n");
  EXPECT_THROW(ctk::config::load(recursive, files.dir("other4"),
                                 files.dir("h4"), files.dir("e4")),
               std::runtime_error);
}

TEST(NetworkConfig, RejectsYaml11BooleansAndFloatsWhereStringsAreRequired) {
  ConfigTree files;
  for (const auto &[name, host] :
       {std::pair{"boolean", "yes"}, std::pair{"float", "1.25"}}) {
    const std::string suffix(name);
    const auto directory = files.dir(suffix);
    auto config = files.write(directory, "config.yaml",
                              "network:\n  transport: tcp\n  tcp:\n    host: " +
                                  std::string(host) + "\n    port: 50051\n");
    EXPECT_THROW(ctk::config::load(config, files.dir(suffix + "-cwd"),
                                   files.dir(suffix + "-home"),
                                   files.dir(suffix + "-etc")),
                 std::runtime_error);
  }
}

TEST(NetworkConfig, RejectsImplicitTimestampsButAcceptsQuotedSocketPaths) {
  ConfigTree files;
  const auto cwd = files.dir("cwd");
  const auto home = files.dir("home");
  const auto system = files.dir("system");
  for (const auto &[name, timestamp] :
       {std::pair{"date", "2026-10-05"},
        std::pair{"datetime", "2026-10-05T10:20:30Z"}}) {
    const std::string suffix(name);
    const auto directory = files.dir(suffix);
    auto implicit = files.write(
        directory, "implicit.yaml",
        "network:\n  unix:\n    socket_path: " + std::string(timestamp) + "\n");
    EXPECT_THROW(ctk::config::load(implicit, cwd, home, system),
                 std::runtime_error);

    auto quoted = files.write(directory, "quoted.yaml",
                              "network:\n  unix:\n    socket_path: \"" +
                                  std::string(timestamp) + "\"\n");
    const auto settings = ctk::config::load(quoted, cwd, home, system);
    EXPECT_EQ(settings.endpoint,
              "unix://" + (directory / timestamp).lexically_normal().string());
  }
}

} // namespace
