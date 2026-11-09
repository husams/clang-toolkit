#include "workspace.hpp"
#include "ctk/support/algorithm.hpp"

#include <algorithm>

#include <google/protobuf/message.h>
#include <llvm/ADT/DenseMap.h>
#include <llvm/ADT/STLExtras.h>
#include <llvm/ADT/StringSet.h>
#include <llvm/Support/Base64.h>

#include "file_values.hpp"
#include "semantic.hpp"
#include "value_access.hpp"

namespace ctk::jit {
namespace {

using namespace value_access;
namespace json = llvm::json;
constexpr std::size_t page_size = 50;
constexpr std::size_t max_rows = 300;
constexpr std::size_t max_depth = 8;
// The frontend retains 20 visible trees. One response can contain several.
constexpr std::size_t max_results = 64;

json::Object typed(llvm::StringRef kind, json::Value data) {
  return json::Object{{"kind", kind}, {"data", std::move(data)}};
}

class Projection {
public:
  explicit Projection(const json::Object* request)
      : request(request) {
    if (request) {
      if (const auto* names = request->getArray("expanded")) {
        for (const auto& name : *names) {
          if (const auto text = name.getAsString()) {
            expanded.insert(*text);
          }
        }
      }
    }
  }

  json::Value project(const Value& value, const std::string& reference, unsigned depth = 0) {
    if (!remaining || depth > max_depth) {
      return typed("opaque", "truncated");
    }
    --remaining;
    if (const auto* text = as<std::string>(value)) {
      auto size = std::min<std::size_t>(text->size(), request ? 4096 : 24000);
      while (size < text->size() && size &&
             (static_cast<unsigned char>((*text)[size]) & 0xc0) == 0x80) {
        --size;
      }
      return llvm::StringRef(*text).take_front(size);
    }
    if (const auto* flag = as<bool>(value)) {
      return *flag;
    }
    if (const auto* integer = as<std::int64_t>(value)) {
      return *integer;
    }
    if (const auto* number = as<double>(value)) {
      return *number;
    }
    if (const auto* seq = object<Sequence>(value)) {
      if (seq->semantic_collection) {
        return semantic_collection(*seq->semantic_collection);
      }
      const auto kind = seq->match_snapshot ? "matches" : seq->tuple ? "tuple" : "list";
      return collection(kind, reference, seq->items.size(), depth, [&](std::size_t index) {
        return project(seq->items[index], reference + "[" + std::to_string(index) + "]", depth + 1);
      });
    }
    if (const auto* record = object<Record>(value)) {
      if (record->semantic_collection) {
        return semantic_collection(*record->semantic_collection);
      }
      if (record->match_row) {
        auto snapshot = match_row_snapshot(*record);
        if (snapshot) {
          return typed("match_row", std::move(*snapshot));
        }
        llvm::consumeError(snapshot.takeError());
        return typed("opaque", "MatchRow");
      }
      return collection("record", reference, record->keys.size(), depth, [&](std::size_t index) {
        const auto& key = record->keys[index];
        std::string child = reference + "[";
        llvm::raw_string_ostream out(child);
        out << json::Value(key) << ']';
        return json::Array{key, project(record->fields.at(key), child, depth + 1)};
      });
    }
    if (const auto* node = object<NativeNode>(value)) {
      auto projection = preview_message_for(Value{semantic(*node)});
      if (auto* object = projection.getAsObject(); object && object->getString("type")) {
        (*object)["kind"] = "binding";
        (*object)["name"] = node->binding_name;
        (*object)["index"] = node->row_index;
        if (auto path = native_source_file(node->ast)) {
          (*object)["path"] = std::move(*path);
        }
      }
      return projection;
    }
    if (const auto* ast = as<AstHandle>(value)) {
      auto path = native_source_file(*ast);
      return typed("tree", path.value_or("<input>"));
    }
    if (const auto* entry = object<FileEntry>(value)) {
      return typed(entry->directory ? "directory" : "file",
                   json::Object{{"path", entry->path},
                                {"absolute", entry->absolute},
                                {"size", entry->size},
                                {"modified", entry->modified}});
    }
    if (const auto* flag = as<SemanticEnum>(value)) {
      return typed("enum", json::Array{flag->name, flag->number});
    }
    if (const auto* matcher = as<MatcherValue>(value)) {
      return typed("matcher", matcher->text);
    }
    if (object<Runnable>(value)) {
      return typed("opaque", "RunnableBlock");
    }
    if (as<BuiltinFunction>(value)) {
      return typed("opaque", "function");
    }
    return preview_message_for(value);
  }

  json::Object globals(const Bindings& bindings) {
    std::vector<llvm::StringRef> names;
    for (const auto& entry : bindings) {
      names.push_back(entry.first());
    }
    llvm::sort(names);
    json::Object data;
    for (const auto name : llvm::ArrayRef(names).take_front(100)) {
      data[name] = project(bindings.at(name), "$" + name.str());
    }
    return data;
  }

private:
  static json::Value preview_message_for(const Value& value) {
    const auto* message = semantic_message(value);
    if (!message) {
      return nullptr;
    }
    auto payload = preview_message(*message);
    auto& fields = *payload.getAsObject();
    if (!fields.getString("type")) {
      return payload;
    }
    if (const auto* semantic = object<SemanticValue>(value)) {
      for (auto& [key, metadata] : semantic_preview_metadata(*semantic)) {
        fields[key] = std::move(metadata);
      }
    }
    if (message->GetDescriptor()->name() == "FileInfo" && semantic_has_live_resource(value)) {
      fields["kind"] = "file_handle";
    }
    if (semantic_has_live_resource(value)) {
      fields["retained"] = true;
    }
    return payload;
  }

  static json::Value semantic_collection(const SemanticCollection& collection) {
    auto payload = preview_message_for(Value{collection.owner});
    if (auto* object = payload.getAsObject(); object && object->getString("type")) {
      (*object)["field"] = collection.field;
    }
    return payload;
  }

  template <typename Item>
  json::Value collection(llvm::StringRef kind, const std::string& reference, std::size_t total,
                         unsigned depth, Item item) {
    json::Array children;
    std::size_t start = 0;
    if (request && total) {
      if (const auto* pages = request->getObject("pages")) {
        const auto page = pages->getInteger(reference).value_or(0);
        if (page > 0) {
          start = std::min<std::size_t>(page, (total - 1) / page_size) * page_size;
        }
      }
    }
    if (!request || (depth < max_depth && ctk::compat::contains(expanded, reference))) {
      const auto stop = std::min(total, start + (request ? page_size : max_rows));
      for (auto index = start; index < stop && remaining; ++index) {
        children.push_back(item(index));
      }
    }
    return json::Object{{"kind", kind},
                        {"length", static_cast<std::int64_t>(total)},
                        {"start", static_cast<std::int64_t>(start)},
                        {"data", std::move(children)}};
  }

  const json::Object* request;
  llvm::StringSet<> expanded;
  std::size_t remaining = max_rows;
};

Value freeze(const Value& source, llvm::DenseMap<const void*, Value>& copies, unsigned depth = 0) {
  if (depth > max_depth) {
    return {};
  }
  if (const auto* sequence = object<Sequence>(source)) {
    if (auto copy = copies.find(sequence); copy != copies.end()) {
      return copy->second;
    }
    auto result = std::make_shared<Sequence>(*sequence);
    copies.try_emplace(sequence, Value{result});
    for (auto& item : result->items) {
      item = freeze(item, copies, depth + 1);
    }
    return {std::move(result)};
  }
  if (const auto* record = object<Record>(source)) {
    if (auto copy = copies.find(record); copy != copies.end()) {
      return copy->second;
    }
    auto result = std::make_shared<Record>(*record);
    copies.try_emplace(record, Value{result});
    for (auto& entry : result->fields) {
      entry.second = freeze(entry.second, copies, depth + 1);
    }
    return {std::move(result)};
  }
  return source;
}

std::string root(llvm::StringRef kind, const Value& value) {
  if (kind == "file_list") {
    return "$Files";
  }
  if (kind == "session_list") {
    return "$Sessions";
  }
  if (const auto* seq = object<Sequence>(value)) {
    return seq->match_snapshot ? "$Matches" : "$List";
  }
  if (const auto* rec = object<Record>(value)) {
    return rec->match_row ? "$Matches" : "$Dictionary";
  }
  if (object<NativeNode>(value)) {
    return "$Matches";
  }
  const auto* message = semantic_message(value);
  if (message && message->GetDescriptor()->name() == "DiscoverFilesResponse") {
    return "$Files";
  }
  return {};
}

} // namespace

llvm::json::Value preview_message(const google::protobuf::Message& message) {
  constexpr std::size_t max_message_bytes = 2 * 1024 * 1024;
  if (message.ByteSizeLong() > max_message_bytes) {
    return typed("opaque", std::string(message.GetDescriptor()->name()));
  }
  return llvm::json::Object{{"kind", "message"},
                            {"type", std::string(message.GetDescriptor()->full_name())},
                            {"data", llvm::encodeBase64(message.SerializeAsString())}};
}

llvm::json::Value preview_value(const Value& value) {
  return Projection(nullptr).project(value, "");
}

void Workspace::progress(llvm::json::Object event) const {
  events(llvm::json::Object{{"progress", std::move(event)}});
}

void Workspace::durable(const google::protobuf::Message& run) const {
  events(llvm::json::Object{{"durable", preview_message(run)}});
}

bool Workspace::capture(Values& runtime, llvm::StringRef kind, const Value& value,
                        llvm::StringRef key) {
  if (runtime.consume_depth || runtime.match_output || !runtime.state.output_path.empty() ||
      (kind != "bindings_list" && root(kind, value).empty())) {
    return false;
  }
  llvm::DenseMap<const void*, Value> copies;
  if (results.size() == max_results) {
    results.pop_front();
  }
  const auto id = next_id++;
  results.push_back({id, kind.str(), freeze(value, copies)});
  runtime.previews.push_back({runtime.output.size(), id, kind.str(), key.str(), {}});
  ++runtime.emissions;
  return true;
}

llvm::json::Value Workspace::outline(const llvm::json::Object& request) const {
  Projection projection(&request);
  const auto id = request.getInteger("result");
  if (!id) {
    return projection.globals(bindings);
  }
  for (const auto& result : results) {
    if (result.id != *id) {
      continue;
    }
    if (result.kind == "bindings_list") {
      const auto* record = object<Record>(result.value);
      return record ? projection.globals(record->fields) : json::Object{};
    }
    return projection.project(result.value, root(result.kind, result.value));
  }
  return nullptr;
}

} // namespace ctk::jit
