#include "ctk/config/config.hpp"

#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <gtest/gtest.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

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

TEST(NetworkConfig, DefaultsToTemporaryUnixEndpointWithoutResponseWireCap) {
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
  EXPECT_EQ(settings.server_grpc.max_send_message_bytes, -1);
  EXPECT_EQ(settings.client_grpc.max_receive_message_bytes, -1);
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

TEST(NetworkConfig, ExposesTypedDefaultsAndWinningValueOrigins) {
  ConfigTree files;
  const auto system = files.dir("system");
  const auto home = files.dir("home");
  const auto cwd = files.dir("project");
  const auto system_file =
      files.write(system, "clang-toolkit.yaml",
                  "network:\n  unix:\n    socket_path: sockets/ctk.sock\n"
                  "client:\n  grpc:\n    max_send_message_bytes: 1024\n");
  const auto hidden_file = files.write(
      home, ".clang-toolkit.yaml", "client:\n  grpc: {}\npool:\n  size: 7\n");
  const auto selected =
      files.write(files.dir("selected"), "config.yaml", "queue:\n  size: 9\n");
  const auto settings = ctk::config::load(selected, cwd, home, system);
  EXPECT_EQ(settings.provenance.at("network.unix.socket_path"),
            system_file.string());
  EXPECT_EQ(settings.provenance.at("client.grpc.max_send_message_bytes"),
            system_file.string());
  EXPECT_EQ(settings.provenance.at("pool.size"), hidden_file.string());
  EXPECT_EQ(settings.provenance.at("queue.size"), selected.string());
  EXPECT_EQ(settings.provenance.at("session.max_files"), "<defaults>");
  EXPECT_EQ(std::get<std::string>(
                settings.effective_values.at("network.unix.socket_path")),
            "sockets/ctk.sock");
  EXPECT_EQ(std::get<std::int64_t>(settings.effective_values.at("pool.size")),
            7);
  EXPECT_TRUE(std::holds_alternative<std::monostate>(
      settings.effective_values.at("client.rpc_timeout_ms")));
  EXPECT_FALSE(settings.provenance.contains("network.tcp.host"));
  EXPECT_EQ(std::get<std::int64_t>(settings.effective_values.at(
                "client.grpc.max_receive_message_bytes")),
            -1);
}

TEST(NetworkConfig, ExplicitStringsAndEmptyNullsKeepYamlScalarTypes) {
  ConfigTree files;
  const auto cwd = files.dir("cwd");
  const auto home = files.dir("home");
  const auto system = files.dir("system");
  auto numeric = files.write(cwd, "numeric.yaml", "pool:\n  size: !!str 1\n");
  EXPECT_THROW(ctk::config::load(numeric, cwd, home, system),
               std::runtime_error);
  auto strings =
      files.write(cwd, "strings.yaml",
                  "network:\n  unix:\n    socket_path: &name !!str null\n");
  auto settings = ctk::config::load(strings, cwd, home, system);
  EXPECT_EQ(settings.endpoint, "unix://" + (cwd / "null").string());
  EXPECT_EQ(std::get<std::string>(
                settings.effective_values.at("network.unix.socket_path")),
            "null");
  auto empty =
      files.write(cwd, "empty.yaml", "network:\n  unix:\n    socket_path:\n");
  settings = ctk::config::load(empty, cwd, home, system);
  EXPECT_EQ(settings.endpoint,
            "unix://" +
                (std::filesystem::temp_directory_path() / "ctk.sock").string());
  EXPECT_EQ(settings.provenance.at("network.unix.socket_path"), empty.string());
  EXPECT_TRUE(std::holds_alternative<std::monostate>(
      settings.effective_values.at("network.unix.socket_path")));
  auto explicit_integer =
      files.write(cwd, "integer.yaml", "pool:\n  size: !!int '4'\n");
  EXPECT_EQ(ctk::config::load(explicit_integer, cwd, home, system).pool_size,
            4);
}

TEST(NetworkConfig, ScalarResolutionMatchesSharedYaml11Types) {
  ConfigTree files;
  const auto cwd = files.dir("cwd");
  const auto home = files.dir("home");
  const auto system = files.dir("system");
  for (const auto &scalar : {"0x10", "1_000", "+3", "1.0e+3", ".inf"}) {
    auto path = files.write(
        cwd, "scalar.yaml",
        std::string("network:\n  unix:\n    socket_path: ") + scalar + "\n");
    EXPECT_THROW(ctk::config::load(path, cwd, home, system), std::runtime_error)
        << scalar;
  }
  for (const auto &scalar : {"1e3", "1.0e3", "inf", "nan", "!!str 0x10"}) {
    auto path = files.write(
        cwd, "scalar.yaml",
        std::string("network:\n  unix:\n    socket_path: ") + scalar + "\n");
    EXPECT_NO_THROW(ctk::config::load(path, cwd, home, system)) << scalar;
  }
}

TEST(NetworkConfig, DiagnosticsIncludeFullKeyAndOriginatingFile) {
  ConfigTree files;
  const auto cwd = files.dir("cwd");
  const auto home = files.dir("home");
  const auto system = files.dir("system");
  for (const auto &[source, key] :
       {std::pair{"pool:\n  size: 1\n  size: 2\n", "pool.size"},
        std::pair{"pool:\n  size: [1]\n", "pool.size"},
        std::pair{"version: 2\n", "version"},
        std::pair{"network:\n  transport: tcp\n", "network.tcp.host"}}) {
    const auto path = files.write(cwd, "bad.yaml", source);
    try {
      ctk::config::load(path, cwd, home, system);
      FAIL() << "invalid configuration was accepted";
    } catch (const std::runtime_error &error) {
      EXPECT_NE(std::string(error.what()).find(path.string()),
                std::string::npos);
      EXPECT_NE(std::string(error.what()).find(key), std::string::npos);
    }
  }
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

TEST(NetworkConfig, SharedRuntimeConfigurationConformance) {
  const auto fixture = std::filesystem::path(__FILE__)
                           .parent_path()
                           .parent_path()
                           .parent_path() /
                       "tests/fixtures/network_configuration.json";
  std::ifstream input(fixture);
  ASSERT_TRUE(input) << fixture;
  std::stringstream source;
  source << input.rdbuf();
  google::protobuf::Struct document;
  const auto parsed =
      google::protobuf::util::JsonStringToMessage(source.str(), &document);
  ASSERT_TRUE(parsed.ok()) << parsed.ToString();
  const auto &layers = document.fields().at("layers").struct_value().fields();
  const auto &cases = document.fields().at("cases").list_value().values();
  ASSERT_GT(cases.size(), 0);
  for (const auto &item : cases) {
    const auto &test = item.struct_value().fields();
    SCOPED_TRACE(test.at("name").string_value());
    ConfigTree files;
    const auto system = files.dir("etc");
    const auto home = files.dir("home");
    const auto cwd = files.dir("project");
    std::vector<std::filesystem::path> supplied_files;
    std::optional<std::filesystem::path> selected;
    for (const auto &[role, contents] :
         test.at("files").struct_value().fields()) {
      const auto path = files.root() / layers.at(role).string_value();
      std::filesystem::create_directories(path.parent_path());
      std::ofstream(path) << contents.string_value();
      supplied_files.push_back(path);
      if (role == "explicit")
        selected = path;
    }
    const auto error_key = test.find("error_key");
    const bool expect_error =
        error_key != test.end() ||
        (test.find("error") != test.end() && test.at("error").bool_value());
    auto expand = [&](std::string text) {
      for (const auto &[marker, value] :
           {std::pair{"${ROOT}", files.root().string()},
            std::pair{"${TEMP}",
                      std::filesystem::temp_directory_path().string()}}) {
        std::size_t offset = 0;
        while ((offset = text.find(marker, offset)) != std::string::npos) {
          text.replace(offset, std::string(marker).size(), value);
          offset += value.size();
        }
      }
      if (text.starts_with("unix://"))
        text =
            "unix://" +
            std::filesystem::path(text.substr(7)).lexically_normal().string();
      return text;
    };
    try {
      const auto settings = ctk::config::load(selected, cwd, home, system);
      if (expect_error) {
        ADD_FAILURE() << "invalid configuration was accepted";
        continue;
      }
      const auto &expected = test.at("expected").struct_value().fields();
      EXPECT_EQ(settings.endpoint,
                expand(expected.at("target").string_value()));
      if (const auto values = expected.find("values"); values != expected.end())
        for (const auto &[key, value] :
             values->second.struct_value().fields()) {
          ASSERT_TRUE(settings.effective_values.contains(key)) << key;
          const auto &actual = settings.effective_values.at(key);
          if (value.kind_case() == google::protobuf::Value::kNullValue)
            EXPECT_TRUE(std::holds_alternative<std::monostate>(actual)) << key;
          else if (value.kind_case() == google::protobuf::Value::kStringValue) {
            const auto *text = std::get_if<std::string>(&actual);
            ASSERT_NE(text, nullptr) << key;
            EXPECT_EQ(*text, value.string_value()) << key;
          } else {
            const auto *number = std::get_if<std::int64_t>(&actual);
            ASSERT_NE(number, nullptr) << key;
            EXPECT_EQ(*number, static_cast<std::int64_t>(value.number_value()))
                << key;
          }
        }
      if (const auto origins = expected.find("origins");
          origins != expected.end())
        for (const auto &[key, value] :
             origins->second.struct_value().fields()) {
          ASSERT_TRUE(settings.provenance.contains(key)) << key;
          EXPECT_EQ(settings.provenance.at(key), expand(value.string_value()))
              << key;
        }
    } catch (const std::runtime_error &error) {
      if (!expect_error) {
        ADD_FAILURE() << error.what();
        continue;
      }
      const std::string message(error.what());
      if (error_key != test.end())
        EXPECT_NE(message.find(error_key->second.string_value()),
                  std::string::npos)
            << message;
      EXPECT_TRUE(std::any_of(supplied_files.begin(), supplied_files.end(),
                              [&](const auto &path) {
                                return message.find(path.string()) !=
                                       std::string::npos;
                              }))
          << message;
    }
  }
}

} // namespace
