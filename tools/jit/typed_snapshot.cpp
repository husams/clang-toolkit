#include "typed_snapshot.hpp"

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

llvm::Error pack(const Value& value, SavedData& output, unsigned depth, std::size_t& remaining) {
  if (depth > max_depth)
    return invalid("snapshot nesting limit exceeded");
  if (!remaining)
    return invalid("snapshot exceeds item limit");
  --remaining;
  auto& fields = *output.mutable_record_value()->mutable_fields();
  auto& type = fields["type"];
  auto& data = fields["value"];
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
    type.set_string_value("list");
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
  if (record.fields_size() != 2 || !type || !type->has_string_value() || !data)
    return invalid("invalid typed value envelope");
  const llvm::StringRef kind(type->string_value());
  if (kind == "null" && data->has_null_value() && data->null_value() == SavedData::NULL_VALUE)
    return Value{};
  if (kind == "bool" && data->has_bool_value())
    return Value{data->bool_value()};
  if (kind == "int" && data->has_integer_value()) {
    std::int64_t number;
    if (!llvm::StringRef(data->integer_value()).getAsInteger(10, number))
      return Value{number};
    return invalid("snapshot integer exceeds the CTK integer range");
  }
  if (kind == "float" && data->has_float_value())
    return Value{data->float_value()};
  if ((kind == "str" || kind == "qualified_name") && data->has_string_value())
    return Value{data->string_value()};
  if (kind == "matcher" && data->has_record_value()) {
    const auto& entries = data->record_value();
    const auto* name = field(entries, "name");
    const auto* arguments = field(entries, "arguments");
    const auto* binding = field(entries, "binding");
    if (!name || !name->has_string_value() || name->string_value().empty() || !arguments ||
        !arguments->has_list_value() || arguments->list_value().items_size() > max_items ||
        !binding || (!binding->has_string_value() && !binding->has_null_value()))
      return invalid("invalid matcher snapshot");
    Sequence args;
    for (const auto& item : arguments->list_value().items()) {
      auto value = unpack(item, depth + 1);
      if (!value)
        return value.takeError();
      if (!as<MatcherValue>(*value) && (value->data.index() == 0 || value->data.index() > 4))
        return invalid("invalid matcher snapshot argument");
      args.items.push_back(std::move(*value));
    }
    return Value{matcher_value(name->string_value(), args,
                               binding->has_string_value() ? std::optional{binding->string_value()}
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
    if (!name || !name->has_string_value() || !wire)
      return invalid("invalid binding snapshot");
    auto value = unpack(*wire, depth + 1);
    if (!value)
      return value.takeError();
    auto record = std::make_shared<Record>();
    record->set("name", {name->string_value()});
    record->set("value", std::move(*value));
    if (const auto* path = field(entries, "source_file"); path && path->has_string_value())
      record->set("source_file", {path->string_value()});
    return Value{std::move(record)};
  }
  if (kind == "semantic_enum" && data->has_record_value()) {
    const auto& entries = data->record_value();
    const auto* name = field(entries, "name");
    const auto* number = field(entries, "number");
    int enum_number;
    if (entries.fields_size() == 2 && name && name->has_string_value() && number &&
        number->has_integer_value() &&
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
    return list(std::move(items));
  }
  if (kind == "record" && data->has_record_value()) {
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
