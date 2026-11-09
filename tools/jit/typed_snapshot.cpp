#include "typed_snapshot.hpp"
#include "file_values.hpp"

#include "match/v1/saved_value.pb.h"
#include "semantic.hpp"
#include "value_access.hpp"

#include <google/protobuf/io/coded_stream.h>
#include <google/protobuf/io/zero_copy_stream_impl_lite.h>

namespace ctk::jit {
namespace {

using namespace value_access;
using ctk::match::v1::SavedData;
using ctk::match::v1::SavedRecord;
using ctk::match::v1::SavedValue;
constexpr unsigned max_depth = 64;

llvm::Error invalid(llvm::StringRef message) {
  return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
}

llvm::Error pack_json(const llvm::json::Value& value, SavedData& output, unsigned depth,
                      std::size_t& remaining) {
  if (!remaining || depth > max_depth)
    return invalid("semantic snapshot exceeds the value limit");
  --remaining;
  if (value.getAsNull())
    output.set_null_value(SavedData::NULL_VALUE);
  else if (const auto boolean = value.getAsBoolean())
    output.set_bool_value(*boolean);
  else if (const auto integer = value.getAsInteger())
    output.set_integer_value(std::to_string(*integer));
  else if (const auto number = value.getAsNumber())
    output.set_float_value(*number);
  else if (const auto text = value.getAsString())
    output.set_string_value(text->str());
  else if (const auto* items = value.getAsArray()) {
    auto* list = output.mutable_list_value();
    for (const auto& item : *items)
      if (auto error = pack_json(item, *list->add_items(), depth + 1, remaining))
        return error;
  } else if (const auto* record = value.getAsObject()) {
    auto& fields = *output.mutable_record_value()->mutable_fields();
    for (const auto& [key, item] : *record)
      if (auto error = pack_json(item, fields[key.str()], depth + 1, remaining))
        return error;
  }
  return llvm::Error::success();
}

llvm::Expected<llvm::json::Value> unpack_json(const SavedData& data, unsigned depth) {
  if (depth > max_depth)
    return invalid("semantic snapshot exceeds the nesting limit");
  switch (data.value_case()) {
  case SavedData::kNullValue:
    return llvm::json::Value(nullptr);
  case SavedData::kBoolValue:
    return llvm::json::Value(data.bool_value());
  case SavedData::kIntegerValue: {
    std::int64_t number;
    if (llvm::StringRef(data.integer_value()).getAsInteger(10, number))
      return invalid("semantic snapshot integer is out of range");
    return llvm::json::Value(number);
  }
  case SavedData::kFloatValue:
    return llvm::json::Value(data.float_value());
  case SavedData::kStringValue:
    return llvm::json::Value(data.string_value());
  case SavedData::kListValue: {
    llvm::json::Array result;
    for (const auto& item : data.list_value().items()) {
      auto value = unpack_json(item, depth + 1);
      if (!value)
        return value.takeError();
      result.push_back(std::move(*value));
    }
    return llvm::json::Value(std::move(result));
  }
  case SavedData::kRecordValue: {
    llvm::json::Object result;
    for (const auto& [key, item] : data.record_value().fields()) {
      auto value = unpack_json(item, depth + 1);
      if (!value)
        return value.takeError();
      result[key] = std::move(*value);
    }
    return llvm::json::Value(std::move(result));
  }
  default:
    return invalid("invalid semantic snapshot");
  }
}

Value snapshot_data(const llvm::json::Value& json) {
  if (const auto* mapping = json.getAsObject()) {
    auto result = std::make_shared<Record>();
    for (const auto& [key, value] : *mapping)
      result->set(key, snapshot_data(value));
    return {std::move(result)};
  }
  if (const auto* sequence = json.getAsArray()) {
    std::vector<Value> result;
    for (const auto& item : *sequence)
      result.push_back(snapshot_data(item));
    return list(std::move(result));
  }
  if (const auto text = json.getAsString()) return {text->str()};
  if (const auto flag = json.getAsBoolean()) return {*flag};
  if (const auto number = json.getAsInteger()) return {*number};
  if (const auto number = json.getAsNumber()) return {*number};
  return {};
}

llvm::Error pack(const Value& value, SavedData& output, unsigned depth, std::size_t& remaining) {
  if (depth > max_depth)
    return invalid("snapshot nesting limit exceeded");
  if (!remaining)
    return invalid("snapshot exceeds item limit");
  --remaining;
  if (const auto* row = object<Record>(value); row && row->match_row) {
    auto snapshot = match_row_snapshot(*row);
    if (!snapshot)
      return snapshot.takeError();
    ++remaining;
    return pack(snapshot_data(llvm::json::Value(std::move(*snapshot))), output, depth,
                remaining);
  }
  auto& fields = *output.mutable_record_value()->mutable_fields();
  auto& type = fields["type"];
  auto& data = fields["value"];
  const auto* sequence = object<Sequence>(value);
  const auto* record = object<Record>(value);
  const auto* collection =
      sequence && sequence->semantic_collection ? &*sequence->semantic_collection
      : record && record->semantic_collection ? &*record->semantic_collection
      : nullptr;
  if (collection) {
    type.set_string_value(sequence ? "semantic_repeated" : "semantic_map");
    auto snapshot = semantic_snapshot(*collection->owner, collection->field);
    if (!snapshot)
      return snapshot.takeError();
    return pack_json(llvm::json::Value(std::move(*snapshot)), data, depth + 1, remaining);
  }
  if (std::holds_alternative<std::monostate>(value.data)) {
    type.set_string_value("null");
    data.set_null_value(SavedData::NULL_VALUE);
  } else if (const auto* boolean = as<bool>(value)) {
    type.set_string_value("bool");
    data.set_bool_value(*boolean);
  } else if (const auto* number = as<std::int64_t>(value)) {
    type.set_string_value("int");
    data.set_integer_value(std::to_string(*number));
  } else if (const auto* number = as<double>(value)) {
    type.set_string_value("float");
    data.set_float_value(*number);
  } else if (const auto* text = as<std::string>(value)) {
    type.set_string_value("str");
    data.set_string_value(*text);
  } else if (const auto* items = object<Sequence>(value); items && !items->tuple) {
    type.set_string_value(items->match_snapshot ? "match_snapshot" : "list");
    auto& list = *data.mutable_list_value();
    for (const auto& item : items->items)
      if (auto error = pack(item, *list.add_items(), depth + 1, remaining))
        return error;
  } else if (const auto* record = object<Record>(value)) {
    type.set_string_value("record");
    auto& entries = *data.mutable_record_value()->mutable_fields();
    for (const auto& key : record->keys)
      if (auto error = pack(record->fields.find(key)->second, entries[key], depth + 1, remaining))
        return error;
  } else if (const auto* entry = object<FileEntry>(value)) {
    type.set_string_value(entry->directory ? "directory" : "file");
    auto& data_fields = *data.mutable_record_value()->mutable_fields();
    data_fields["path"].set_string_value(entry->path);
    data_fields["absolute"].set_string_value(entry->absolute);
    data_fields["modified"].set_string_value(entry->modified);
    data_fields["size"].set_integer_value(std::to_string(entry->size));
  } else if (const auto* matcher = as<MatcherValue>(value)) {
    type.set_string_value("matcher");
    auto& entries = *data.mutable_record_value()->mutable_fields();
    entries["name"].set_string_value(matcher->name);
    if (matcher->binding)
      entries["binding"].set_string_value(*matcher->binding);
    else
      entries["binding"].set_null_value(SavedData::NULL_VALUE);
    auto* arguments = entries["arguments"].mutable_list_value();
    for (const auto& arg : matcher->arguments->items) {
      if (auto error = pack(arg, *arguments->add_items(), depth + 1, remaining))
        return error;
    }
  } else if (const auto* view = object<SemanticValue>(value)) {
    type.set_string_value("semantic_message");
    auto snapshot = semantic_snapshot(*view);
    if (!snapshot)
      return snapshot.takeError();
    return pack_json(llvm::json::Value(std::move(*snapshot)), data, depth + 1, remaining);
  } else if (const auto* node = object<NativeNode>(value)) {
    type.set_string_value("binding_snapshot");
    const auto view = semantic(*node);
    if (!view)
      return invalid("cannot detach native binding");
    auto& entries = *data.mutable_record_value()->mutable_fields();
    entries["name"].set_string_value(node->binding_name);
    if (const auto path = native_source_file(node->ast))
      entries["source_file"].set_string_value(*path);
    return pack(Value{view}, entries["value"], depth + 1, remaining);
  } else if (const auto* enumeration = as<SemanticEnum>(value)) {
    type.set_string_value("semantic_enum");
    auto& entries = *data.mutable_record_value()->mutable_fields();
    entries["name"].set_string_value(enumeration->name);
    entries["number"].set_integer_value(std::to_string(enumeration->number));
  } else {
    return invalid("value has no standalone typed snapshot representation");
  }
  return llvm::Error::success();
}

const SavedData* field(const SavedRecord& record, const char* name) {
  const auto found = record.fields().find(name);
  return found == record.fields().end() ? nullptr : &found->second;
}

llvm::Expected<Value> unpack(const SavedData& envelope, unsigned depth) {
  if (depth > max_depth)
    return invalid("snapshot nesting limit exceeded");
  const auto& record = envelope.record_value();
  const auto* type = field(record, "type");
  const auto* data = field(record, "value");
  if (record.fields_size() != 2 || !type || type->value_case() != SavedData::kStringValue || !data)
    return invalid("invalid typed value envelope");
  const llvm::StringRef kind(type->string_value());
  if (kind == "null" && data->value_case() == SavedData::kNullValue && data->null_value() == SavedData::NULL_VALUE)
    return Value{};
  if (kind == "bool" && data->value_case() == SavedData::kBoolValue)
    return Value{data->bool_value()};
  if (kind == "int" && data->value_case() == SavedData::kIntegerValue) {
    std::int64_t number;
    if (!llvm::StringRef(data->integer_value()).getAsInteger(10, number))
      return Value{number};
    return invalid("snapshot integer exceeds the CTK integer range");
  }
  if (kind == "float" && data->value_case() == SavedData::kFloatValue)
    return Value{data->float_value()};
  if ((kind == "str" || kind == "qualified_name") && data->value_case() == SavedData::kStringValue)
    return Value{data->string_value()};
  if ((kind == "file" || kind == "directory") && data->has_record_value()) {
    const auto& fields = data->record_value();
    const auto* path = field(fields, "path");
    const auto* absolute = field(fields, "absolute");
    const auto* modified = field(fields, "modified");
    const auto* size = field(fields, "size");
    std::int64_t bytes;
    if (fields.fields_size() != 4 || !path || path->value_case() != SavedData::kStringValue ||
        !absolute || absolute->value_case() != SavedData::kStringValue || !modified || modified->value_case() != SavedData::kStringValue ||
        !size || size->value_case() != SavedData::kIntegerValue ||
        llvm::StringRef(size->integer_value()).getAsInteger(10, bytes))
      return invalid("invalid file snapshot");
    return Value{std::make_shared<FileEntry>(FileEntry{path->string_value(),
        absolute->string_value(), modified->string_value(), bytes, kind == "directory"})};
  }
  if (kind == "matcher" && data->has_record_value()) {
    const auto& entries = data->record_value();
    const auto* name = field(entries, "name");
    const auto* arguments = field(entries, "arguments");
    const auto* binding = field(entries, "binding");
    if (!name || name->value_case() != SavedData::kStringValue || name->string_value().empty() || !arguments ||
        !arguments->has_list_value() || arguments->list_value().items_size() > max_items ||
        !binding || (binding->value_case() != SavedData::kStringValue && binding->value_case() != SavedData::kNullValue))
      return invalid("invalid matcher snapshot");
    Sequence args;
    for (const auto& item : arguments->list_value().items()) {
      auto value = unpack(item, depth + 1);
      if (!value)
        return value.takeError();
      if (!as<MatcherValue>(*value) && !object<FileEntry>(*value) &&
          (value->data.index() == 0 || value->data.index() > 4))
        return invalid("invalid matcher snapshot argument");
      args.items.push_back(std::move(*value));
    }
    return Value{matcher_value(name->string_value(), args,
                               binding->value_case() == SavedData::kStringValue ? std::optional{binding->string_value()}
                                                           : std::nullopt)};
  }
  if (kind == "semantic_message" || kind == "semantic_repeated" || kind == "semantic_map") {
    auto metadata = unpack_json(*data, depth + 1);
    if (!metadata)
      return metadata.takeError();
    if (!metadata->getAsObject())
      return invalid("invalid semantic snapshot envelope");
    return restore_semantic_snapshot(*metadata->getAsObject());
  }
  if (kind == "binding_snapshot" && data->has_record_value()) {
    const auto& entries = data->record_value();
    const auto* name = field(entries, "name");
    const auto* wire = field(entries, "value");
    if (!name || name->value_case() != SavedData::kStringValue || !wire)
      return invalid("invalid binding snapshot");
    auto value = unpack(*wire, depth + 1);
    if (!value)
      return value.takeError();
    auto record = std::make_shared<Record>();
    record->set("name", {name->string_value()});
    record->set("value", std::move(*value));
    if (const auto* path = field(entries, "source_file"); path && path->value_case() == SavedData::kStringValue)
      record->set("source_file", {path->string_value()});
    return Value{std::move(record)};
  }
  if (kind == "semantic_enum" && data->has_record_value()) {
    const auto& entries = data->record_value();
    const auto* name = field(entries, "name");
    const auto* number = field(entries, "number");
    int enum_number;
    if (entries.fields_size() == 2 && name && name->value_case() == SavedData::kStringValue && number &&
        number->value_case() == SavedData::kIntegerValue &&
        !llvm::StringRef(number->integer_value()).getAsInteger(10, enum_number))
      return Value{SemanticEnum{name->string_value(), enum_number}};
  }
  if ((kind == "list" || kind == "match_snapshot") && data->has_list_value()) {
    std::vector<Value> items;
    if (data->list_value().items_size() > max_items)
      return invalid("snapshot exceeds item limit");
    for (const auto& item : data->list_value().items()) {
      auto decoded = unpack(item, depth + 1);
      if (!decoded)
        return decoded.takeError();
      items.push_back(std::move(*decoded));
    }
    auto result = list(std::move(items));
    object<Sequence>(result)->match_snapshot = kind == "match_snapshot";
    return result;
  }
  if ((kind == "record" || kind == "semantic_bindings") && data->has_record_value()) {
    auto result = std::make_shared<Record>();
    const auto& entries = data->record_value().fields();
    if (entries.size() > max_items)
      return invalid("snapshot exceeds item limit");
    std::vector<llvm::StringRef> keys;
    for (const auto& [key, _] : entries)
      keys.push_back(key);
    llvm::sort(keys);
    for (const auto key : keys) {
      auto value = unpack(entries.at(key.str()), depth + 1);
      if (!value)
        return value.takeError();
      result->set(key, std::move(*value));
    }
    return Value{std::move(result)};
  }
  return invalid("invalid or unsupported typed snapshot value");
}

} // namespace

llvm::Expected<std::string> encode_snapshot(const Value& value) {
  SavedValue snapshot;
  snapshot.set_schema_version(1);
  auto remaining = max_items;
  if (auto error = pack(value, *snapshot.mutable_envelope(), 0, remaining))
    return std::move(error);
  std::string bytes;
  google::protobuf::io::StringOutputStream stream(&bytes);
  {
    google::protobuf::io::CodedOutputStream coded(&stream);
    coded.SetSerializationDeterministic(true);
    if (!snapshot.SerializeToCodedStream(&coded))
      return invalid("could not encode typed snapshot");
  }
  return bytes;
}

llvm::Expected<Value> decode_snapshot(llvm::StringRef bytes) {
  SavedValue snapshot;
  google::protobuf::io::CodedInputStream coded(reinterpret_cast<const std::uint8_t*>(bytes.data()),
                                               static_cast<int>(bytes.size()));
  coded.SetRecursionLimit(max_depth * 4);
  if (!snapshot.ParseFromCodedStream(&coded) || !coded.ConsumedEntireMessage() ||
      snapshot.schema_version() != 1 || !snapshot.has_envelope())
    return invalid("invalid or unsupported typed snapshot");
  return unpack(snapshot.envelope(), 0);
}

} // namespace ctk::jit
