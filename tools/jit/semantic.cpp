#include "semantic.hpp"
#include "analysis/v1/call_graph_response.pb.h"
#include "match/v1/resources.pb.h"
#include "serialization/match_metadata_helpers.hpp"
#include "serialization/node_serializers.hpp"
#include "value_access.hpp"

#include <limits>

#include <google/protobuf/descriptor.h>
#include <google/protobuf/message.h>
#include <google/protobuf/util/json_util.h>
#include <llvm/ADT/StringSet.h>
#include <llvm/ADT/StringSwitch.h>

namespace ctk::jit {
namespace pb = google::protobuf;
namespace ast = ctk::ast::v1;
namespace match = ctk::match::v1;
namespace ser = clang_layer::serialization;
using namespace value_access;

struct SemanticValue {
  std::shared_ptr<const pb::Message> owner;
  const pb::Message* message;
  std::string path;
  std::vector<const ast::FieldAvailability*> availability;
  std::shared_ptr<const std::vector<std::shared_ptr<NativeNode>>> graph_nodes;
  std::shared_ptr<NativeNode> selected;
};

namespace {

llvm::Error fail(const llvm::Twine& message) {
  return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
}

void add_availability(SemanticValue& value) {
  const auto& message = *value.message;
  const auto* field = message.GetDescriptor()->FindFieldByName("availability");
  if (!field || !field->is_repeated() ||
      field->message_type() != ast::FieldAvailability::descriptor()) {
    return;
  }
  const auto& reflection = *message.GetReflection();
  for (int i = 0; i < reflection.FieldSize(message, field); ++i) {
    value.availability.push_back(static_cast<const ast::FieldAvailability*>(
        &reflection.GetRepeatedMessage(message, field, i)));
  }
}

SemanticValue child(const SemanticValue& parent, const pb::Message& message, llvm::StringRef name) {
  SemanticValue result{parent.owner, &message, (llvm::Twine(parent.path) + "." + name).str(),
                       parent.availability, parent.graph_nodes};
  if (result.graph_nodes &&
      message.GetDescriptor() == ctk::analysis::v1::CallGraphNode::descriptor()) {
    const auto& node = static_cast<const ctk::analysis::v1::CallGraphNode&>(message);
    if (node.has_native_match_index() && node.native_match_index() < result.graph_nodes->size())
      result.selected = (*result.graph_nodes)[node.native_match_index()];
  }
  add_availability(result);
  return result;
}

const ast::FieldAvailability* availability(const SemanticValue& value, llvm::StringRef field) {
  const auto path = (llvm::Twine(value.path) + "." + field).str();
  const auto message = value.message->GetDescriptor()->name();
  for (const auto* item : value.availability) {
    const llvm::StringRef key(item->field_path());
    if (key.empty())
      continue;
    if (key == field || key == path || key == (llvm::Twine(message) + "." + field).str() ||
        llvm::StringRef(path).ends_with((llvm::Twine(".") + key).str())) {
      return item;
    }
  }
  return nullptr;
}

llvm::StringRef status(const SemanticValue& value, const pb::FieldDescriptor& field) {
  if (const auto* state = availability(value, field.name())) {
    switch (static_cast<int>(state->state())) {
    case 0:
      return "UNSPECIFIED";
    case 2:
      return "SEMANTICALLY_ABSENT";
    case 3:
      return "UNREQUESTED";
    case 4:
      return "INAPPLICABLE";
    case 5:
      return "UNAVAILABLE";
    case 6:
      return "TRUNCATED";
    default:
      break;
    }
  }
  if (field.has_presence() && !value.message->GetReflection()->HasField(*value.message, &field))
    return "ABSENT";
  return "PRESENT";
}

llvm::Error missing(const SemanticValue& value, const pb::FieldDescriptor& field,
                    llvm::StringRef state) {
  const auto detail = llvm::StringSwitch<llvm::StringRef>(state)
                          .Case("SEMANTICALLY_ABSENT", "field is semantically absent")
                          .Case("UNREQUESTED", "field was not requested")
                          .Case("INAPPLICABLE", "field is inapplicable")
                          .Case("UNAVAILABLE", "field is unavailable")
                          .Case("TRUNCATED", "field was truncated")
                          .Case("UNSPECIFIED", "field state is unspecified")
                          .Default("field is absent");
  return fail(llvm::Twine(detail) + ": " + value.path + "." + field.name());
}

const pb::FieldDescriptor* payload(const pb::Message& message) {
  const auto* descriptor = message.GetDescriptor();
  llvm::StringRef oneof;
  if (descriptor == ast::AstNode::descriptor())
    oneof = "payload";
  else if (descriptor == match::MatchBinding::descriptor())
    oneof = "value";
  else
    return nullptr;
  const auto* field = message.GetReflection()->GetOneofFieldDescriptor(
      message, descriptor->FindOneofByName(oneof.str()));
  return field && field->name() != "unsupported" ? field : nullptr;
}

const pb::FieldDescriptor* base(const pb::Descriptor& descriptor) {
  // Same declaration field-1 inheritance chain as the console's semantic view.
  if (!llvm::StringRef(descriptor.full_name()).starts_with("ctk.ast.v1."))
    return nullptr;
  const auto field =
      llvm::StringSwitch<llvm::StringRef>(descriptor.name())
          .Cases({"CXXRecordDecl", "ClassTemplateSpecializationDecl",
                  "ClassTemplatePartialSpecializationDecl", "RecordDecl"},
                 "record")
          .Case("RecordDeclInfo", "tag")
          .Case("TagDeclInfo", "type_declaration")
          .Case("TypeDeclInfo", "named")
          .Cases({"FunctionDecl", "CXXDeductionGuideDecl", "CXXMethodDeclInfo"}, "function")
          .Cases({"CXXMethodDecl", "CXXConstructorDecl", "CXXDestructorDecl", "CXXConversionDecl"},
                 "method")
          .Case("FunctionDeclInfo", "declarator")
          .Case("DeclaratorDeclInfo", "value")
          .Case("ValueDeclInfo", "named")
          .Case("NamedDeclInfo", "declaration")
          .Default("");
  return field.empty() ? nullptr : descriptor.FindFieldByName(field.str());
}

std::optional<SemanticValue> next_owner(const SemanticValue& value) {
  const auto* field = payload(*value.message);
  if (!field)
    field = base(*value.message->GetDescriptor());
  if (!field || status(value, *field) != "PRESENT")
    return std::nullopt;
  return child(value, value.message->GetReflection()->GetMessage(*value.message, field),
               field->name());
}

struct Field {
  SemanticValue owner;
  const pb::FieldDescriptor* descriptor;
};

std::optional<Field> find_field(SemanticValue value, llvm::StringRef name) {
  for (auto owner = std::optional<SemanticValue>(std::move(value)); owner;
       owner = next_owner(*owner)) {
    const auto* field = owner->message->GetDescriptor()->FindFieldByName(name.str());
    if (field)
      return Field{std::move(*owner), field};
  }
  return std::nullopt;
}

llvm::Expected<Value> scalar(const SemanticValue& owner, const pb::FieldDescriptor& field,
                             int index = -1) {
  const auto& msg = *owner.message;
  const auto& ref = *msg.GetReflection();
  const auto* f = &field;
  switch (field.cpp_type()) {
  case pb::FieldDescriptor::CPPTYPE_INT32:
    return Value{static_cast<std::int64_t>(index < 0 ? ref.GetInt32(msg, f)
                                                     : ref.GetRepeatedInt32(msg, f, index))};
  case pb::FieldDescriptor::CPPTYPE_INT64:
    return Value{index < 0 ? ref.GetInt64(msg, f) : ref.GetRepeatedInt64(msg, f, index)};
  case pb::FieldDescriptor::CPPTYPE_UINT32:
    return Value{static_cast<std::int64_t>(index < 0 ? ref.GetUInt32(msg, f)
                                                     : ref.GetRepeatedUInt32(msg, f, index))};
  case pb::FieldDescriptor::CPPTYPE_UINT64: {
    const auto value = index < 0 ? ref.GetUInt64(msg, f) : ref.GetRepeatedUInt64(msg, f, index);
    if (value > std::numeric_limits<std::int64_t>::max()) {
      return fail("unsigned semantic field exceeds the CTK integer range");
    }
    return Value{static_cast<std::int64_t>(value)};
  }
  case pb::FieldDescriptor::CPPTYPE_DOUBLE:
    return Value{index < 0 ? ref.GetDouble(msg, f) : ref.GetRepeatedDouble(msg, f, index)};
  case pb::FieldDescriptor::CPPTYPE_FLOAT:
    return Value{static_cast<double>(index < 0 ? ref.GetFloat(msg, f)
                                               : ref.GetRepeatedFloat(msg, f, index))};
  case pb::FieldDescriptor::CPPTYPE_BOOL:
    return Value{index < 0 ? ref.GetBool(msg, f) : ref.GetRepeatedBool(msg, f, index)};
  case pb::FieldDescriptor::CPPTYPE_STRING:
    return Value{index < 0 ? ref.GetString(msg, f) : ref.GetRepeatedString(msg, f, index)};
  case pb::FieldDescriptor::CPPTYPE_ENUM: {
    const auto number =
        index < 0 ? ref.GetEnumValue(msg, f) : ref.GetRepeatedEnumValue(msg, f, index);
    const auto* named = field.enum_type()->FindValueByNumber(number);
    return Value{SemanticEnum{
        named ? std::string(named->name()) : "UNKNOWN_" + std::to_string(number), number}};
  }
  case pb::FieldDescriptor::CPPTYPE_MESSAGE: {
    const auto& message =
        index < 0 ? ref.GetMessage(msg, f) : ref.GetRepeatedMessage(msg, f, index);
    return Value{std::make_shared<SemanticValue>(child(owner, message, field.name()))};
  }
  }
  return fail("invalid semantic field type");
}

llvm::Expected<Value> read(const SemanticValue& owner, const pb::FieldDescriptor& field) {
  const auto state = status(owner, field);
  if (state != "PRESENT")
    return missing(owner, field, state);
  if (!field.is_repeated())
    return scalar(owner, field);

  const auto& msg = *owner.message;
  const auto& ref = *msg.GetReflection();
  const auto size = ref.FieldSize(msg, &field);
  if (field.is_map()) {
    auto mapping = std::make_shared<Record>();
    for (int i = 0; i < size; ++i) {
      const auto& entry = ref.GetRepeatedMessage(msg, &field, i);
      const auto* key = entry.GetDescriptor()->map_key();
      const auto* descriptor = entry.GetDescriptor()->map_value();
      if (key->cpp_type() != pb::FieldDescriptor::CPPTYPE_STRING)
        return fail("semantic map keys must be strings");
      auto value = scalar(child(owner, entry, field.name()), *descriptor);
      if (!value)
        return value.takeError();
      mapping->set(entry.GetReflection()->GetString(entry, key), std::move(*value));
    }
    return Value{std::move(mapping)};
  }
  std::vector<Value> items;
  items.reserve(size);
  for (int i = 0; i < size; ++i) {
    auto item = scalar(owner, field, i);
    if (!item)
      return item.takeError();
    items.push_back(std::move(*item));
  }
  return list(std::move(items));
}

} // namespace

SemanticHandle semantic(std::unique_ptr<pb::Message> message) {
  auto* address = message.get();
  auto view = std::make_shared<SemanticValue>(SemanticValue{
      std::move(message), address, std::string(address->GetDescriptor()->full_name()), {}});
  add_availability(*view);
  return view;
}

SemanticHandle semantic(const NativeNode& node) {
  if (!node.semantic) {
    auto binding = std::make_unique<match::MatchBinding>();
    ser::SerializationContext context{*node.ast, ser::ProjectionPolicy::Shallow};
    if (!ser::NodeSerializerDispatcher::serialize(*node.node, *binding, context) &&
        !binding->has_unsupported())
      return {};
    ser::helpers::write_match_metadata(*node.node, *binding, context);
    binding->add_supported_scopes(match::BINDING_MATCH_SCOPE_CHILDREN);
    node.semantic = semantic(std::move(binding));
  }
  return node.semantic;
}

SemanticHandle semantic_graph(std::unique_ptr<pb::Message> message,
                              std::vector<std::shared_ptr<NativeNode>> nodes) {
  auto result = semantic(std::move(message));
  result->graph_nodes =
      std::make_shared<std::vector<std::shared_ptr<NativeNode>>>(std::move(nodes));
  return result;
}

const pb::Message* semantic_message(const Value& value) {
  const auto* view = object<SemanticValue>(value);
  return view ? view->message : nullptr;
}

const NativeNode* retained_node(const Value& value) {
  if (const auto* direct = object<NativeNode>(value))
    return direct;
  if (const auto* view = object<SemanticValue>(value))
    return view->selected.get();
  return nullptr;
}

std::optional<std::size_t> semantic_length(const Value& value) {
  const auto* proto = semantic_message(value);
  if (!proto || proto->GetDescriptor() != match::DiscoverFilesResponse::descriptor())
    return std::nullopt;
  return static_cast<const match::DiscoverFilesResponse&>(*proto).inputs_size();
}

std::optional<Value> semantic_iteration(const Value& value) {
  const auto* view = object<SemanticValue>(value);
  if (!view)
    return std::nullopt;
  std::vector<Value> items;
  if (view->message->GetDescriptor() == match::DiscoverFilesResponse::descriptor()) {
    const auto& files = static_cast<const match::DiscoverFilesResponse&>(*view->message);
    for (const auto& input : files.inputs()) {
      items.push_back({std::make_shared<SemanticValue>(child(*view, input, "inputs"))});
    }
  } else if (view->graph_nodes &&
             view->message->GetDescriptor() == ctk::analysis::v1::CallGraphResponse::descriptor()) {
    const auto& graph = static_cast<const ctk::analysis::v1::CallGraphResponse&>(*view->message);
    for (const auto& node : graph.nodes()) {
      if (!node.is_virtual_root() && node.node_index() != graph.root_node()) {
        items.push_back({std::make_shared<SemanticValue>(child(*view, node, "nodes"))});
      }
    }
  } else {
    return std::nullopt;
  }
  return list(std::move(items));
}

llvm::Expected<Value> semantic_field(const SemanticValue& value, llvm::StringRef name) {
  const auto* descriptor = value.message->GetDescriptor();
  if (descriptor == match::FileInfo::descriptor()) {
    const auto& info = static_cast<const match::FileInfo&>(*value.message);
    if (name == "path")
      return Value{info.input().file_path()};
    if (name == "profile_id")
      return Value{info.input().profile().profile_id()};
    if (name == "state")
      return Value{static_cast<std::int64_t>(info.state())};
  }
  if (descriptor == match::InputDescriptor::descriptor()) {
    const auto& input = static_cast<const match::InputDescriptor&>(*value.message);
    if (name == "path")
      return Value{input.file_path()};
    if (name == "profile_id")
      return Value{input.profile().profile_id()};
    if (name == "working_directory")
      return Value{input.profile().working_directory()};
    if (name == "compilation_database")
      return Value{input.profile().compilation_database()};
    if (name == "frozen_profile")
      return Value{input.profile().frozen()};
    if (name == "compile_arguments") {
      std::vector<Value> arguments;
      for (const auto& arg : input.profile().compile_arguments())
        arguments.push_back({arg});
      return list(std::move(arguments), true);
    }
  }
  if (value.selected && name == "binding")
    return Value{value.selected};
  if (value.graph_nodes && (name == "response" || name == "proto") &&
      value.message == value.owner.get()) {
    return Value{std::make_shared<SemanticValue>(value)};
  }
  if (auto field = find_field(value, name))
    return read(field->owner, *field->descriptor);
  if (name == "keys") {
    std::vector<Value> result;
    llvm::StringSet<> seen;
    for (auto owner = std::optional<SemanticValue>(value); owner; owner = next_owner(*owner)) {
      const auto* descriptor = owner->message->GetDescriptor();
      for (int index = 0; index < descriptor->field_count(); ++index) {
        const auto* field = descriptor->field(index);
        if (seen.insert(field->name()).second && status(*owner, *field) == "PRESENT")
          result.push_back({std::string(field->name())});
      }
    }
    return list(std::move(result));
  }
  return fail(llvm::Twine("unknown semantic field: ") + name);
}

llvm::Expected<Value> semantic_method(const SemanticValue& value, llvm::StringRef name,
                                      const Sequence& arguments) {
  if (value.graph_nodes &&
      value.message->GetDescriptor() == ctk::analysis::v1::CallGraphResponse::descriptor() &&
      name == "function") {
    const auto& args = arguments.items;
    const auto* query = args.empty() ? nullptr : as<std::string>(args[0]);
    const auto* requested = args.empty() ? nullptr : retained_node(args[0]);
    const auto* signature = args.size() == 2 ? as<std::string>(args[1]) : nullptr;
    if ((!query && !requested) || args.size() > 2 || (args.size() == 2 && !signature)) {
      return fail(
          "function requires a qualified name and optional signature, or one retained binding");
    }
    const auto& graph = static_cast<const ctk::analysis::v1::CallGraphResponse&>(*value.message);
    const ctk::analysis::v1::CallGraphNode* found = nullptr;
    for (const auto& node : graph.nodes()) {
      if (!node.has_function())
        continue;
      if (requested) {
        if (!node.has_native_match_index() ||
            node.native_match_index() >= value.graph_nodes->size())
          continue;
        const auto& native = (*value.graph_nodes)[node.native_match_index()];
        if (native->ast != requested->ast ||
            native->node->getMemoizationData() != requested->node->getMemoizationData())
          continue;
      } else if (node.function().qualified_name() != *query ||
                 (signature && node.function().type().spelling() != *signature)) {
        continue;
      }
      if (found)
        return fail("call graph function is ambiguous; supply its signature");
      found = &node;
    }
    if (!found)
      return fail("call graph function was not found");
    return Value{std::make_shared<SemanticValue>(child(value, *found, "nodes"))};
  }
  if (name != "fieldOr" && name != "fieldState" && name != "hasField")
    return fail(llvm::Twine("unknown semantic method: ") + name);
  const bool fallback = name == "fieldOr";
  const auto& args = arguments.items;
  const auto* key = args.size() == (fallback ? 2 : 1) ? as<std::string>(args[0]) : nullptr;
  if (!key)
    return fail(llvm::Twine(name) + " requires a string field name");
  const auto field = find_field(value, *key);
  if (!field)
    return fail(llvm::Twine("unknown semantic field: ") + *key);
  const auto state = status(field->owner, *field->descriptor);
  if (name == "fieldState")
    return Value{state.str()};
  if (fallback) {
    if (state == "SEMANTICALLY_ABSENT" || state == "INAPPLICABLE" || state == "ABSENT")
      return args[1];
    return read(field->owner, *field->descriptor);
  }
  if (state == "UNREQUESTED")
    return fail(llvm::Twine("field was not requested: ") + *key + "; use fieldState");
  if (!field->descriptor->has_presence())
    return fail(llvm::Twine("field has no presence: ") + *key);
  return Value{
      field->owner.message->GetReflection()->HasField(*field->owner.message, field->descriptor)};
}

bool semantic_kind(const SemanticValue& value, llvm::StringRef kind) {
  if (kind == "CXXRecord")
    kind = "CXXRecordDecl";
  auto owner = value;
  while (const auto* field = payload(*owner.message)) {
    owner = child(owner, owner.message->GetReflection()->GetMessage(*owner.message, field),
                  field->name());
  }
  return llvm::StringRef(owner.message->GetDescriptor()->name()) == kind;
}

std::string semantic_json(const SemanticValue& value, bool indented) {
  pb::util::JsonPrintOptions options;
  options.add_whitespace = indented;
  options.preserve_proto_field_names = true;
  std::string result;
  const auto status = pb::util::MessageToJsonString(*value.message, &result, options);
  return status.ok() ? result : status.ToString();
}

} // namespace ctk::jit
