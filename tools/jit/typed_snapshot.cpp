#include "typed_snapshot.hpp"

#include "match/v1/saved_value.pb.h"
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
