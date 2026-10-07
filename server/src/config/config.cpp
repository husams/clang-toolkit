#include "ctk/config/config.hpp"
#include "ctk/platform/loopback_address.hpp"

#include <yaml.h>

#include <algorithm>
#include <cctype>
#include <charconv>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <limits>
#include <map>
#include <memory>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <variant>
#include <vector>

namespace ctk::config {
namespace {

constexpr std::string_view kStringTag = "tag:yaml.org,2002:str";
constexpr std::string_view kIntTag = "tag:yaml.org,2002:int";
constexpr std::string_view kNullTag = "tag:yaml.org,2002:null";
constexpr std::string_view kMapTag = "tag:yaml.org,2002:map";

struct Node {
  using Map = std::map<std::string, Node, std::less<>>;
  std::variant<std::monostate, std::string, Map> value;
  std::string tag;
  bool plain_scalar{false};
  bool explicit_string{false};
  std::filesystem::path origin;
};

using Documents = std::vector<Node>;

[[noreturn]] void fail(const std::string &message) {
  throw std::runtime_error(message);
}

std::string where(const Node &node) {
  return node.origin.empty() ? std::string("configuration")
                             : node.origin.string();
}

Node convert_node(yaml_document_t &document, yaml_node_t *raw,
                  const std::filesystem::path &origin,
                  std::set<yaml_node_t *> &active,
                  const std::set<std::size_t> &explicit_strings,
                  std::size_t depth = 0,
                  const std::string &key_path = "configuration") {
  constexpr std::size_t kMaximumDepth = 64;
  if (!raw)
    fail(origin.string() + ": invalid YAML node reference");
  if (depth >= kMaximumDepth)
    fail(origin.string() + ": " + key_path +
         ": YAML nesting exceeds the supported depth");
  if (!active.insert(raw).second)
    fail(origin.string() + ": " + key_path +
         ": recursive YAML aliases are not supported");
  struct ActiveGuard {
    std::set<yaml_node_t *> &active;
    yaml_node_t *node;
    ~ActiveGuard() { active.erase(node); }
  } active_guard{active, raw};

  Node result;
  result.origin = origin;
  result.tag = reinterpret_cast<const char *>(raw->tag);
  result.explicit_string = explicit_strings.contains(raw->start_mark.index);
  if (raw->type == YAML_SCALAR_NODE) {
    if (result.tag != kStringTag && result.tag != kIntTag &&
        result.tag != kNullTag)
      fail(where(result) + ": " + key_path + ": unsupported YAML scalar tag '" +
           result.tag + "'");
    result.plain_scalar = raw->data.scalar.style == YAML_PLAIN_SCALAR_STYLE;
    const auto *bytes = reinterpret_cast<const char *>(raw->data.scalar.value);
    std::string scalar(bytes, raw->data.scalar.length);
    if (result.tag == kNullTag ||
        (raw->data.scalar.style == YAML_PLAIN_SCALAR_STYLE &&
         !result.explicit_string &&
         (scalar.empty() || scalar == "null" || scalar == "Null" ||
          scalar == "NULL" || scalar == "~"))) {
      result.value = std::monostate{};
    } else {
      result.value = std::move(scalar);
    }
    return result;
  }
  if (raw->type == YAML_SEQUENCE_NODE)
    fail(where(result) + ": " + key_path +
         ": sequences are not valid configuration values");
  if (raw->type != YAML_MAPPING_NODE)
    fail(where(result) + ": unsupported YAML node");
  if (result.tag != kMapTag)
    fail(where(result) + ": unsupported YAML mapping tag '" + result.tag + "'");
  Node::Map entries;
  for (auto pair = raw->data.mapping.pairs.start;
       pair != raw->data.mapping.pairs.top; ++pair) {
    yaml_node_t *key_node = yaml_document_get_node(&document, pair->key);
    if (!key_node || key_node->type != YAML_SCALAR_NODE ||
        std::string_view(reinterpret_cast<const char *>(key_node->tag)) !=
            kStringTag) {
      fail(where(result) + ": " + key_path + ": mapping keys must be strings");
    }
    const std::string key(
        reinterpret_cast<const char *>(key_node->data.scalar.value),
        key_node->data.scalar.length);
    const auto child_path =
        key_path == "configuration" ? key : key_path + "." + key;
    if (entries.contains(key))
      fail(where(result) + ": duplicate key '" + child_path + "'");
    yaml_node_t *child = yaml_document_get_node(&document, pair->value);
    entries.emplace(key, convert_node(document, child, origin, active,
                                      explicit_strings, depth + 1, child_path));
  }
  result.value = std::move(entries);
  return result;
}

class YamlConfigReader {
public:
  Node read(const std::filesystem::path &path) const {
    std::ifstream input(path, std::ios::binary);
    if (!input)
      fail("cannot read configuration file: " + path.string());
    std::string source((std::istreambuf_iterator<char>(input)),
                       std::istreambuf_iterator<char>());
    const auto explicit_strings = string_tags(source, path);
    yaml_parser_t parser;
    if (!yaml_parser_initialize(&parser))
      fail("cannot initialize YAML parser");
    struct ParserGuard {
      yaml_parser_t *value;
      ~ParserGuard() { yaml_parser_delete(value); }
    } guard{&parser};
    yaml_parser_set_input_string(
        &parser, reinterpret_cast<const unsigned char *>(source.data()),
        source.size());
    yaml_document_t document;
    if (!yaml_parser_load(&parser, &document)) {
      std::ostringstream message;
      message << path << ':' << parser.problem_mark.line + 1 << ':'
              << parser.problem_mark.column + 1 << ": invalid YAML: "
              << (parser.problem ? parser.problem : "parse error");
      fail(message.str());
    }
    struct DocumentGuard {
      yaml_document_t *value;
      ~DocumentGuard() { yaml_document_delete(value); }
    } doc_guard{&document};
    if (yaml_document_get_root_node(&document) == nullptr)
      fail(path.string() + ": empty YAML document");
    std::set<yaml_node_t *> active;
    Node result = convert_node(document, yaml_document_get_root_node(&document),
                               path, active, explicit_strings);
    if (!std::holds_alternative<Node::Map>(result.value))
      fail(path.string() + ": document root must be a mapping");
    yaml_document_t next_document;
    if (!yaml_parser_load(&parser, &next_document))
      fail(path.string() + ": invalid YAML after the first document");
    const bool has_second_document =
        yaml_document_get_root_node(&next_document) != nullptr;
    yaml_document_delete(&next_document);
    if (has_second_document)
      fail(path.string() + ": multiple YAML documents are not supported");
    return result;
  }

private:
  // Document nodes resolve both implicit scalars and !!str to the same tag.
  // Events retain that distinction, including tags following anchors.
  static std::set<std::size_t> string_tags(const std::string &source,
                                           const std::filesystem::path &path) {
    yaml_parser_t parser;
    if (!yaml_parser_initialize(&parser))
      fail("cannot initialize YAML parser");
    struct ParserGuard {
      yaml_parser_t *value;
      ~ParserGuard() { yaml_parser_delete(value); }
    } guard{&parser};
    yaml_parser_set_input_string(
        &parser, reinterpret_cast<const unsigned char *>(source.data()),
        source.size());
    std::set<std::size_t> result;
    for (;;) {
      yaml_event_t event;
      if (!yaml_parser_parse(&parser, &event)) {
        std::ostringstream message;
        message << path << ':' << parser.problem_mark.line + 1 << ':'
                << parser.problem_mark.column + 1 << ": invalid YAML: "
                << (parser.problem ? parser.problem : "parse error");
        fail(message.str());
      }
      const bool complete = event.type == YAML_STREAM_END_EVENT;
      if (event.type == YAML_SCALAR_EVENT && event.data.scalar.tag &&
          std::string_view(reinterpret_cast<const char *>(
              event.data.scalar.tag)) == kStringTag)
        result.insert(event.start_mark.index);
      yaml_event_delete(&event);
      if (complete)
        return result;
    }
  }
};

class ConfigFileDiscovery {
public:
  std::vector<std::filesystem::path>
  discover(const std::optional<std::filesystem::path> &cli,
           const std::filesystem::path &cwd, const std::filesystem::path &home,
           const std::filesystem::path &system) const {
    std::vector<std::filesystem::path> paths;
    append_layer(paths, system, {"clang-toolkit.yaml"});
    append_layer(paths, home, {"clang-toolkit.yaml", ".clang-toolkit.yaml"});
    append_layer(paths, cwd, {"clang-toolkit.yaml", ".clang-toolkit.yaml"});
    if (cli) {
      auto selected = cli->is_absolute() ? *cli : cwd / *cli;
      if (!std::filesystem::exists(selected))
        fail("explicit configuration file does not exist: " +
             selected.string());
      if (!std::filesystem::is_regular_file(selected))
        fail("explicit configuration path is not a file: " + selected.string());
      paths.push_back(std::filesystem::absolute(selected).lexically_normal());
    }
    return paths;
  }

private:
  static void append_layer(std::vector<std::filesystem::path> &output,
                           const std::filesystem::path &directory,
                           const std::vector<std::string> &names) {
    if (directory.empty())
      return;
    for (const auto &name : names) {
      auto path = directory / name;
      if (std::filesystem::exists(path)) {
        if (!std::filesystem::is_regular_file(path))
          fail("configuration path is not a file: " + path.string());
        output.push_back(std::filesystem::absolute(path).lexically_normal());
      }
    }
  }
};

const Node::Map &mapping(const Node &node, std::string_view path) {
  const auto *value = std::get_if<Node::Map>(&node.value);
  if (!value)
    fail(where(node) + ": " + std::string(path) + " must be a mapping");
  return *value;
}

const Node *child(const Node &node, std::string_view key) {
  const auto *map = std::get_if<Node::Map>(&node.value);
  if (!map)
    return nullptr;
  auto it = map->find(key);
  return it == map->end() ? nullptr : &it->second;
}

std::string scalar(const Node &node, std::string_view path) {
  const auto *value = std::get_if<std::string>(&node.value);
  if (!value || node.tag != kStringTag)
    fail(where(node) + ": " + std::string(path) + " must be a string");
  if (value->find('\0') != std::string::npos)
    fail(where(node) + ": " + std::string(path) +
         " must not contain a NUL byte");
  std::string lowered = *value;
  std::transform(
      lowered.begin(), lowered.end(), lowered.begin(),
      [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  if (node.plain_scalar && !node.explicit_string) {
    static const std::regex date_pattern(R"(^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}$)");
    static const std::regex datetime_pattern(
        R"(^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[Tt]|[ \t]+)[0-9]{1,2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]*)?(?:[ \t]*(?:Z|[-+][0-9]{1,2}(?::[0-9]{2})?))?$)");
    if (std::regex_match(*value, date_pattern) ||
        std::regex_match(*value, datetime_pattern))
      fail(where(node) + ": " + std::string(path) + " must be a string");
    if (lowered == "true" || lowered == "false" || lowered == "yes" ||
        lowered == "no" || lowered == "on" || lowered == "off")
      fail(where(node) + ": " + std::string(path) + " must be a string");
  }
  if (node.plain_scalar && !node.explicit_string && !value->empty()) {
    // Match the shared YAML 1.1 scalar resolver before applying schema types.
    static const std::regex integer_pattern(
        R"(^([-+]?0b[0-1_]+|[-+]?0[0-7_]+|[-+]?(0|[1-9][0-9_]*)|[-+]?0x[0-9a-fA-F_]+|[-+]?[1-9][0-9_]*(:[0-5]?[0-9])+)$)");
    static const std::regex float_pattern(
        R"(^([-+]?[0-9][0-9_]*\.[0-9_]*([eE][-+][0-9]+)?|\.[0-9][0-9_]*([eE][-+][0-9]+)?|[-+]?[0-9][0-9_]*(:[0-5]?[0-9])+\.[0-9_]*|[-+]?\.(inf|Inf|INF)|\.(nan|NaN|NAN))$)");
    if (std::regex_match(*value, integer_pattern) ||
        std::regex_match(*value, float_pattern))
      fail(where(node) + ": " + std::string(path) + " must be a string");
  }
  return *value;
}

std::int64_t integer(const Node &node, std::string_view path) {
  const auto *value = std::get_if<std::string>(&node.value);
  if (!value ||
      (node.tag != kIntTag && (!node.plain_scalar || node.explicit_string)))
    fail(where(node) + ": " + std::string(path) + " must be an integer");
  std::int64_t result{};
  const auto [end, error] =
      std::from_chars(value->data(), value->data() + value->size(), result);
  if (error != std::errc{} || end != value->data() + value->size())
    fail(where(node) + ": " + std::string(path) +
         " must be a base-10 integer in range");
  return result;
}

bool is_null(const Node &node) {
  return std::holds_alternative<std::monostate>(node.value);
}

void ensure_keys(const Node &node, std::string_view path,
                 std::initializer_list<std::string_view> allowed) {
  for (const auto &[key, value] : mapping(node, path)) {
    (void)value;
    if (std::find(allowed.begin(), allowed.end(), key) == allowed.end())
      fail(where(node) + ": unknown key '" + std::string(path) +
           (path.empty() ? "" : ".") + key + "'");
  }
}

void validate_option_integer(
    const Node &node, std::string_view path, bool nullable,
    std::int64_t minimum, bool grpc_special = false,
    std::int64_t maximum = std::numeric_limits<std::int64_t>::max()) {
  if (is_null(node) && nullable)
    return;
  auto value = integer(node, path);
  if (value > maximum)
    fail(where(node) + ": " + std::string(path) +
         " exceeds the supported integer range");
  if (grpc_special && (value == -1 || value > 0))
    return;
  if (value < minimum)
    fail(where(node) + ": " + std::string(path) + " is out of range");
}

void validate_file(const Node &root) {
  ensure_keys(
      root, "",
      {"version", "network", "pool", "queue", "server", "session", "client"});
  if (const Node *v = child(root, "version")) {
    if (integer(*v, "version") != 1)
      fail(where(*v) + ": version: unsupported configuration version");
  }
  if (const Node *n = child(root, "network")) {
    ensure_keys(*n, "network", {"transport", "unix", "tcp"});
    if (const Node *t = child(*n, "transport")) {
      const auto transport = scalar(*t, "network.transport");
      if (transport != "unix" && transport != "tcp")
        fail(where(*t) + ": network.transport must be 'unix' or 'tcp'");
    }
    if (const Node *u = child(*n, "unix")) {
      ensure_keys(*u, "network.unix", {"socket_path"});
      if (const Node *p = child(*u, "socket_path")) {
        if (!is_null(*p)) {
          auto value = scalar(*p, "network.unix.socket_path");
          if (value.empty())
            fail(where(*p) + ": network.unix.socket_path must not be empty");
        }
      }
    }
    if (const Node *t = child(*n, "tcp")) {
      ensure_keys(*t, "network.tcp", {"host", "port"});
      if (const Node *h = child(*t, "host")) {
        const auto host = scalar(*h, "network.tcp.host");
        if (host.empty())
          fail(where(*h) + ": network.tcp.host must not be empty");
        if (!platform::normalize_loopback_address(host))
          fail(where(*h) + ": network.tcp.host must be a loopback IPv4/IPv6 "
                           "address or localhost");
      }
      if (const Node *p = child(*t, "port"))
        validate_option_integer(*p, "network.tcp.port", false, 1, false, 65535);
    }
  }
  if (const Node *p = child(root, "pool")) {
    ensure_keys(*p, "pool", {"size"});
    if (const Node *n = child(*p, "size"))
      validate_option_integer(*n, "pool.size", false, 1, false,
                              std::numeric_limits<int>::max());
  }
  if (const Node *q = child(root, "queue")) {
    ensure_keys(*q, "queue", {"size"});
    if (const Node *n = child(*q, "size"))
      validate_option_integer(*n, "queue.size", false, 1, false,
                              std::numeric_limits<int>::max());
  }
  if (const Node *s = child(root, "session")) {
    ensure_keys(*s, "session", {"max_files", "max_memory_bytes"});
    if (const Node *n = child(*s, "max_files"))
      validate_option_integer(*n, "session.max_files", false, 1, false,
                              std::numeric_limits<int>::max());
    if (const Node *n = child(*s, "max_memory_bytes"))
      validate_option_integer(*n, "session.max_memory_bytes", false, 1);
  }
  auto check_grpc = [](const Node &node, std::string_view path) {
    ensure_keys(node, path,
                {"max_receive_message_bytes", "max_send_message_bytes"});
    for (auto key : {"max_receive_message_bytes", "max_send_message_bytes"})
      if (const Node *n = child(node, key))
        validate_option_integer(*n, std::string(path) + "." + key, true, 1,
                                true, std::numeric_limits<int>::max());
  };
  for (auto section : {"server", "client"})
    if (const Node *n = child(root, section)) {
      if (std::string_view(section) == "server")
        ensure_keys(*n, section, {"grpc", "shutdown_grace_ms"});
      else
        ensure_keys(*n, section, {"grpc", "rpc_timeout_ms"});
      if (const Node *g = child(*n, "grpc"))
        check_grpc(*g, std::string(section) + ".grpc");
      if (section == std::string_view("server")) {
        if (const Node *v = child(*n, "shutdown_grace_ms"))
          validate_option_integer(*v, "server.shutdown_grace_ms", true, 0);
      } else if (const Node *v = child(*n, "rpc_timeout_ms"))
        validate_option_integer(*v, "client.rpc_timeout_ms", true, 1);
    }
}

class ConfigMerger {
public:
  Node merge(const Documents &documents) const {
    Node result;
    result.value = Node::Map{};
    for (const auto &document : documents)
      merge_into(result, document);
    return result;
  }

private:
  static void merge_into(Node &target, const Node &source) {
    const auto *source_map = std::get_if<Node::Map>(&source.value);
    auto *target_map = std::get_if<Node::Map>(&target.value);
    if (source_map && target_map) {
      for (const auto &[key, value] : *source_map) {
        auto [it, inserted] = target_map->try_emplace(key, value);
        if (!inserted)
          merge_into(it->second, value);
      }
    } else {
      target = source;
    }
  }
};

std::optional<std::int64_t> optional_int(const Node *node) {
  return node && !is_null(*node)
             ? std::optional(integer(*node, "optional integer"))
             : std::nullopt;
}

class EndpointResolver {
public:
  static std::string resolve(const Node &root) {
    const Node *network = child(root, "network");
    const Node *transport_node =
        network ? child(*network, "transport") : nullptr;
    const auto transport =
        transport_node ? scalar(*transport_node, "network.transport") : "unix";
    if (transport == "unix") {
      const Node *unix_node = child(network ? *network : root, "unix");
      const Node *path_node =
          unix_node ? child(*unix_node, "socket_path") : nullptr;
      if (!path_node || is_null(*path_node)) {
        const auto path =
            std::filesystem::absolute(std::filesystem::temp_directory_path() /
                                      "ctk.sock")
                .lexically_normal();
        return "unix://" + path.string();
      }
      std::filesystem::path path(
          scalar(*path_node, "network.unix.socket_path"));
      if (path.is_relative())
        path = path_node->origin.parent_path() / path;
      path = std::filesystem::absolute(path).lexically_normal();
      return "unix://" + path.string();
    }
    if (transport != "tcp")
      fail(where(root) + ": network.transport must be 'unix' or 'tcp'");
    const Node *tcp = network ? child(*network, "tcp") : nullptr;
    const Node *host_node = tcp ? child(*tcp, "host") : nullptr;
    const Node *port_node = tcp ? child(*tcp, "port") : nullptr;
    if (!host_node)
      fail(where(transport_node ? *transport_node : root) +
           ": network.tcp.host is required for TCP transport");
    if (!port_node)
      fail(where(transport_node ? *transport_node : root) +
           ": network.tcp.port is required for TCP transport");
    std::string host = scalar(*host_node, "network.tcp.host");
    const auto port = integer(*port_node, "network.tcp.port");
    if (port < 1 || port > 65535)
      fail(where(*port_node) +
           ": network.tcp.port must be between 1 and 65535");
    auto normalized_host = platform::normalize_loopback_address(host);
    if (!normalized_host)
      fail(where(*host_node) + ": network.tcp.host must be a loopback "
                               "IPv4/IPv6 address or localhost");
    return *normalized_host + ":" + std::to_string(port);
  }
};

class ConfigValidator {
public:
  Settings validate(const Node &root) const {
    Settings settings;
    settings.endpoint = EndpointResolver::resolve(root);
    if (const Node *node = child(root, "pool"))
      if (const Node *value = child(*node, "size"))
        settings.pool_size = static_cast<int>(integer(*value, "pool.size"));
    if (const Node *node = child(root, "queue"))
      if (const Node *value = child(*node, "size"))
        settings.queue_size = static_cast<int>(integer(*value, "queue.size"));
    if (const Node *node = child(root, "session")) {
      if (const Node *value = child(*node, "max_files"))
        settings.max_files =
            static_cast<int>(integer(*value, "session.max_files"));
      if (const Node *value = child(*node, "max_memory_bytes"))
        settings.max_memory_bytes = integer(*value, "session.max_memory_bytes");
    }
    auto fill_grpc = [](const Node *section, GrpcSettings &output) {
      if (const Node *grpc = section ? child(*section, "grpc") : nullptr) {
        if (const Node *value = child(*grpc, "max_receive_message_bytes"))
          output.max_receive_message_bytes = optional_int(value);
        if (const Node *value = child(*grpc, "max_send_message_bytes"))
          output.max_send_message_bytes = optional_int(value);
      }
    };
    const Node *server = child(root, "server");
    const Node *client = child(root, "client");
    fill_grpc(server, settings.server_grpc);
    fill_grpc(client, settings.client_grpc);
    settings.shutdown_grace_ms =
        optional_int(server ? child(*server, "shutdown_grace_ms") : nullptr);
    settings.rpc_timeout_ms =
        optional_int(client ? child(*client, "rpc_timeout_ms") : nullptr);
    settings.effective_values = {
        {"version", std::int64_t{1}},
        {"network.transport", std::string{"unix"}},
        {"network.unix.socket_path", std::monostate{}},
        {"pool.size", std::int64_t{3}},
        {"queue.size", std::int64_t{100}},
        {"session.max_files", std::int64_t{100}},
        {"session.max_memory_bytes", std::int64_t{2147483648}},
        {"server.grpc.max_send_message_bytes", std::int64_t{-1}},
        {"client.grpc.max_receive_message_bytes", std::int64_t{-1}},
        {"server.shutdown_grace_ms", std::monostate{}},
        {"client.rpc_timeout_ms", std::monostate{}}};
    for (const auto &[key, value] : settings.effective_values) {
      (void)value;
      settings.provenance[key] = "<defaults>";
    }
    expose_values(root, "", settings);
    return settings;
  }

private:
  static void expose_values(const Node &node, const std::string &path,
                            Settings &settings) {
    if (const auto *map = std::get_if<Node::Map>(&node.value)) {
      for (const auto &[key, value] : *map)
        expose_values(value, path.empty() ? key : path + "." + key, settings);
    } else {
      ConfigValue value;
      if (!is_null(node)) {
        if (path == "network.transport" || path == "network.unix.socket_path" ||
            path == "network.tcp.host")
          value = scalar(node, path);
        else
          value = integer(node, path);
      }
      settings.effective_values[path] = std::move(value);
      settings.provenance[path] = where(node);
    }
  }
};

} // namespace

Settings load(std::optional<std::filesystem::path> cli_file,
              std::filesystem::path cwd,
              std::optional<std::filesystem::path> home,
              std::filesystem::path system_directory) {
  if (!home) {
    const char *environment_home = std::getenv("HOME");
    if (environment_home && *environment_home)
      home = environment_home;
  }
  ConfigFileDiscovery discovery;
  YamlConfigReader reader;
  Documents documents;
  for (const auto &path :
       discovery.discover(cli_file, cwd, home.value_or(std::filesystem::path{}),
                          system_directory)) {
    Node document = reader.read(path);
    validate_file(document);
    documents.push_back(std::move(document));
  }
  Node merged = ConfigMerger{}.merge(documents);
  validate_file(merged);
  return ConfigValidator{}.validate(merged);
}

} // namespace ctk::config
