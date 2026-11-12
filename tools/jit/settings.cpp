#include "settings.hpp"
#include "file_values.hpp"

#include "documents.hpp"
#include "value_access.hpp"

#include <array>
#include <cstdlib>
#include <filesystem>

#include <llvm/ADT/STLExtras.h>
#include <llvm/ADT/Twine.h>

namespace ctk::jit {
namespace {

using namespace value_access;
namespace fs = std::filesystem;

const std::array<llvm::StringRef, 7> keys{
    "traversal", "extra_args", "compile_commands", "cache_dir", "files", "output", "vars"};

std::array<fs::path, 3> locations() {
  const auto* home = std::getenv("HOME");
  return {"/etc/clang_tools/config.yaml",
          home && *home ? fs::path(home) / ".clang_tools.yaml" : fs::path{},
          fs::current_path() / ".clang_tools.yaml"};
}

std::optional<std::array<Record, 3>> read_layers(Values& runtime,
                                                 const std::array<fs::path, 3>& paths) {
  std::array<Record, 3> layers;
  for (std::size_t index = 0; index < paths.size(); ++index) {
    if (paths[index].empty() || !fs::exists(paths[index]))
      continue;
    const auto* value = read_settings_file(runtime, paths[index].string());
    if (!value)
      return std::nullopt;
    if (std::holds_alternative<std::monostate>(value->data))
      continue;
    const auto* map = object<Record>(*value);
    if (!map) {
      runtime.fail(llvm::Twine(paths[index].string()) + ": expected a YAML mapping");
      return std::nullopt;
    }
    for (const auto& key : map->keys) {
      if (!llvm::is_contained(keys, key)) {
        runtime.fail(llvm::Twine("unknown setting: ") + key);
        return std::nullopt;
      }
    }
    layers[index] = *map;
  }
  return layers;
}

Record merged(const std::array<Record, 3>& layers) {
  Record result;
  result.set("traversal", {std::string("AsIs")});
  result.set("extra_args", list());
  result.set("compile_commands", {});
  result.set("cache_dir", {});
  result.set("files", list());
  result.set("output", {std::string("stdout")});
  result.set("vars", record());
  for (const auto& layer : layers) {
    for (const auto& key : layer.keys) {
      const auto& value = layer.fields.find(key)->second;
      if (key == "vars") {
        const auto* mapping = object<Record>(value);
        const auto* previous = object<Record>(result.fields.find("vars")->second);
        if (mapping && previous) {
          auto combined = std::make_shared<Record>(*previous);
          for (const auto& name : mapping->keys)
            combined->set(name, mapping->fields.find(name)->second);
          result.set(key, {std::move(combined)});
          continue;
        }
      }
      result.set(key, value);
    }
  }
  return result;
}

std::optional<std::vector<std::string>> strings(const Value& value) {
  const auto* sequence = object<Sequence>(value);
  if (!sequence || sequence->tuple)
    return std::nullopt;
  std::vector<std::string> result;
  for (const auto& item : sequence->items) {
    const auto* text = as<std::string>(item);
    if (!text)
      return std::nullopt;
    result.push_back(*text);
  }
  return result;
}

bool apply(Values& runtime, const Record& settings, bool initialize, bool validate_only) {
  const auto get = [&](llvm::StringRef name) -> const Value& {
    return settings.fields.find(name)->second;
  };
  const auto* traversal = as<std::string>(get("traversal"));
  const auto arguments = strings(get("extra_args"));
  const auto paths = strings(get("files"));
  const auto* database = as<std::string>(get("compile_commands"));
  const auto* output = as<std::string>(get("output"));
  const auto* vars = object<Record>(get("vars"));
  const char* failure = nullptr;
  if (!traversal || (*traversal != "AsIs" && *traversal != "IgnoreUnlessSpelledInSource"))
    failure = "traversal must be AsIs or IgnoreUnlessSpelledInSource";
  else if (!arguments)
    failure = "extra_args must be a list of strings";
  else if (!paths)
    failure = "files must be a list of paths";
  else if ((database && database->empty()) ||
           (!database && !std::holds_alternative<std::monostate>(get("compile_commands").data)))
    failure = "compile_commands must be a nonempty path string or null";
  else if (!as<std::string>(get("cache_dir")) &&
           !std::holds_alternative<std::monostate>(get("cache_dir").data))
    failure = "cache_dir must be a path string or null";
  else if (!output)
    failure = "output must be stdout or a path string";
  else if (!vars)
    failure = "vars must be a mapping with string keys";
  if (failure) {
    runtime.fail(failure);
    return false;
  }
  if (validate_only)
    return true;
  auto& state = runtime.state;
  state.spelled_only = *traversal == "IgnoreUnlessSpelledInSource";
  state.compilation_arguments = *arguments;
  state.compilation_database = database ? *database : state.default_database;
  state.default_targets = get("files");
  if (initialize) {
    state.output_path = *output == "stdout" ? "" : *output;
    for (const auto& name : vars->keys)
      runtime.globals.try_emplace(name, vars->fields.find(name)->second);
  }
  return true;
}

} // namespace

bool load_settings(Values& runtime) {
  const auto layers = read_layers(runtime, locations());
  return layers && apply(runtime, merged(*layers), true, false);
}

std::filesystem::path configured_script_cache() {
  Bindings bindings;
  LocalState state;
  std::string output, error;
  Values runtime(nullptr, bindings, state, output, error);
  const auto layers = read_layers(runtime, locations());
  if (!layers)
    return {};
  const auto settings = merged(*layers);
  const auto *text = as<std::string>(settings.fields.find("cache_dir")->second);
  if (!text || text->empty())
    return {};
  if (llvm::StringRef(*text).starts_with("~/")) {
    if (const auto *home = std::getenv("HOME"); home && *home)
      return fs::path(home) / text->substr(2);
  }
  return fs::absolute(*text);
}

const Value* update_setting(Values& runtime, llvm::StringRef name, const Value* value, bool user,
                            bool append) {
  if (runtime.state.batch_output_bytes)
    return runtime.fail("settings cannot be changed inside a foreground batch");
  if (!llvm::is_contained(keys, name))
    return runtime.fail(llvm::Twine("unknown setting: ") + name);
  const auto paths = locations();
  const std::size_t index = user ? 1 : 2;
  if (paths[index].empty())
    return runtime.fail("HOME is unavailable for user settings");
  auto layers = read_layers(runtime, paths);
  if (!layers)
    return nullptr;
  auto& layer = (*layers)[index];
  if (append) {
    const auto current = merged(*layers);
    if (!apply(runtime, current, false, true))
      return nullptr;
    auto arguments = object<Sequence>(current.fields.find("extra_args")->second)->items;
    arguments.push_back(*value);
    layer.set(name, list(std::move(arguments)));
  } else if (value && name == "files") {
    const auto* entries = object<Sequence>(*value);
    if (!entries || entries->tuple) return runtime.fail("files setting requires a list of files");
    std::vector<Value> paths;
    for (const auto& item : entries->items) {
      if (const auto* entry = object<FileEntry>(item); entry && !entry->directory)
        paths.push_back({entry->path});
      else if (as<std::string>(item)) paths.push_back(item);
      else return runtime.fail("files setting requires file paths");
    }
    layer.set(name, list(std::move(paths)));
  } else if (value) {
    layer.set(name, *value);
  } else {
    layer.fields.erase(name);
    std::erase(layer.keys, name.str());
  }
  const auto effective = merged(*layers);
  if (!apply(runtime, effective, false, true))
    return nullptr;
  const Value content{std::make_shared<Record>(layer)};
  if (!write_settings_file(runtime, paths[index].string(), content))
    return nullptr;
  if (!apply(runtime, effective, false, false))
    return nullptr;
  if (name == "output") {
    const auto& output = *as<std::string>(effective.fields.find("output")->second);
    runtime.state.output_path = output == "stdout" ? "" : output;
  }
  return runtime.hold({});
}

} // namespace ctk::jit
