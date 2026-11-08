#include "semantic.hpp"
#include "analysis.hpp"
#include "analysis/v1/batch.pb.h"
#include "analysis/v1/call_graph_response.pb.h"
#include "match/v1/match_service.pb.h"
#include "match/v1/resources.pb.h"
#include "serialization/match_metadata_helpers.hpp"
#include "serialization/node_serializers.hpp"
#include "value_access.hpp"

#include <deque>
#include <limits>
#include <map>
#include <set>

#include <clang/AST/ASTContext.h>
#include <clang/Basic/FileManager.h>
#include <clang/Basic/SourceManager.h>
#include <google/protobuf/descriptor.h>
#include <google/protobuf/message.h>
#include <google/protobuf/util/json_util.h>
#include <llvm/ADT/StringSet.h>
#include <llvm/ADT/StringSwitch.h>
#include <llvm/Support/FileSystem.h>
#include <llvm/Support/Path.h>

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
  bool file_handle = false;
  std::shared_ptr<const std::vector<ast::FieldAvailability>> restored_availability;
  std::optional<std::string> streamed_name;
  std::optional<std::string> source_file;
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
  result.restored_availability = parent.restored_availability;
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
    mapping->semantic_collection = SemanticCollection{
        std::make_shared<SemanticValue>(owner), std::string(field.name())};
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
  auto value = list(std::move(items));
  object<Sequence>(value)->semantic_collection = SemanticCollection{
      std::make_shared<SemanticValue>(owner), std::string(field.name())};
  return value;
}

std::optional<Value> node_alias(const SemanticValue& value, llvm::StringRef name,
                                unsigned depth = 0) {
  if (depth > 12)
    return std::nullopt;
  if (const auto field = find_field(value, name)) {
    auto resolved = read(field->owner, *field->descriptor);
    if (resolved)
      return std::move(*resolved);
    llvm::consumeError(resolved.takeError());
  }
  const auto& message = *value.message;
  const auto* descriptor = message.GetDescriptor();
  for (int index = 0; index < descriptor->field_count(); ++index) {
    const auto* field = descriptor->field(index);
    if (field->is_repeated() || !field->message_type() || status(value, *field) != "PRESENT")
      continue;
    const auto& nested = message.GetReflection()->GetMessage(message, field);
    if (auto result = node_alias(child(value, nested, field->name()), name, depth + 1))
      return result;
  }
  return std::nullopt;
}

std::optional<std::string> nested_text(const pb::Message& message, llvm::StringRef name) {
  const auto* reflection = message.GetReflection();
  const auto* field = message.GetDescriptor()->FindFieldByName(name.str());
  if (field && !field->is_repeated() && field->type() == pb::FieldDescriptor::TYPE_STRING) {
    auto text = reflection->GetString(message, field);
    if (!text.empty())
      return text;
  }
  std::vector<const pb::FieldDescriptor*> present;
  reflection->ListFields(message, &present);
  for (const auto* child : present) {
    if (child->cpp_type() != pb::FieldDescriptor::CPPTYPE_MESSAGE)
      continue;
    const auto count = child->is_repeated() ? reflection->FieldSize(message, child) : 1;
    for (int index = 0; index < count; ++index) {
      const auto& sub = child->is_repeated() ? reflection->GetRepeatedMessage(message, child, index)
                                            : reflection->GetMessage(message, child);
      if (auto text = nested_text(sub, name))
        return text;
    }
  }
  return std::nullopt;
}

} // namespace

SemanticHandle semantic(std::unique_ptr<pb::Message> message, bool file_handle) {
  auto* address = message.get();
  auto view = std::make_shared<SemanticValue>(SemanticValue{
      std::move(message), address, std::string(address->GetDescriptor()->full_name()), {}});
  view->file_handle = file_handle;
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

std::optional<std::string> native_source_file(const AstHandle& ast) {
  const auto& sources = ast->getSourceManager();
  const auto file = sources.getFileEntryRefForID(sources.getMainFileID());
  if (!file)
    return std::nullopt;
  llvm::SmallString<256> path(file->getNameAsRequested()), canonical;
  sources.getFileManager().makeAbsolutePath(path);
  if (!llvm::sys::fs::real_path(path, canonical))
    return canonical.str().str();
  llvm::sys::path::remove_dots(path, true);
  return path.str().str();
}

llvm::Expected<llvm::json::Object> match_row_snapshot(const Record& row) {
  auto message = std::make_unique<match::MatchResult>();
  for (const auto& [name, value] : row.fields) {
    const auto* node = object<NativeNode>(value);
    auto binding = node ? semantic(*node) : SemanticHandle{};
    if (!binding)
      return fail("could not detach match row binding");
    (*message->mutable_bindings())[name.str()] =
        static_cast<const match::MatchBinding&>(*binding->message);
  }
  if (row.source_match_index)
    message->set_source_match_index(*row.source_match_index);
  auto json = llvm::json::parse(semantic_json(*semantic(std::move(message)), false));
  if (!json)
    return json.takeError();
  auto* record = json->getAsObject();
  if (!record)
    return fail("invalid match row");
  if (row.source_file)
    (*record)["source_file"] = *row.source_file;
  return std::move(*record);
}

SemanticHandle streamed_binding(const NativeNode& node,
                                const std::optional<std::string>& source_file) {
  const auto binding = semantic(node);
  if (!binding)
    return {};
  auto result = std::make_shared<SemanticValue>(*binding);
  result->streamed_name = node.binding_name;
  result->source_file = source_file;
  return result;
}

bool is_streamed_binding(const Value& value) {
  const auto* view = object<SemanticValue>(value);
  return view && view->streamed_name.has_value();
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

bool semantic_has_live_resource(const Value& value) {
  const auto* view = object<SemanticValue>(value);
  return view && (view->file_handle || view->graph_nodes ||
                  view->message->GetDescriptor() == match::SessionInfo::descriptor());
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

llvm::json::Array semantic_completion_fields(const SemanticValue& value, bool presence) {
  llvm::json::Array fields;
  llvm::StringSet<> seen;
  const auto add = [&](llvm::StringRef name, llvm::StringRef detail, bool method = false) {
    fields.push_back(llvm::json::Object{{"name", name.str()}, {"detail", detail.str()}, {"method", method}});
  };
  for (auto owner = std::optional<SemanticValue>(value); owner; owner = next_owner(*owner)) {
    const auto* descriptor = owner->message->GetDescriptor();
    for (int index = 0; index < descriptor->field_count(); ++index) {
      const auto* field = descriptor->field(index);
      if (!seen.insert(field->name()).second)
        continue;
      if (presence) {
        if (field->has_presence())
          add(field->name(), "field presence");
        continue;
      }
      const auto* oneof = field->real_containing_oneof();
      if (oneof && owner->message->GetReflection()->GetOneofFieldDescriptor(*owner->message, oneof) != field)
        continue;
      if (status(*owner, *field) == "UNREQUESTED")
        continue;
      const bool active = oneof && oneof->field_count() > 1;
      std::string detail = active ? "active field" : "field";
      if (const auto* type = field->message_type())
        detail = active ? "active payload · " + std::string(type->name()) + " · continue with ." :
                          "field · " + std::string(type->name());
      else if (const auto* type = field->enum_type())
        detail += " · " + std::string(type->name());
      add(field->name(), detail);
    }
  }
  if (presence)
    return fields;
  if (!seen.contains("keys"))
    add("keys", "property");
  for (const auto* method : {"fieldOr", "fieldState", "hasField"})
    add(method, "method · checks field presence or reports availability", true);
  return fields;
}

llvm::Expected<Value> semantic_field(const SemanticValue& value, llvm::StringRef name) {
  const auto* descriptor = value.message->GetDescriptor();
  if (value.streamed_name) {
    if (name == "name")
      return Value{*value.streamed_name};
    if (name == "source_file")
      return value.source_file ? Value{*value.source_file} : Value{};
    if (name == "value") {
      auto detached = std::make_shared<SemanticValue>(value);
      detached->streamed_name.reset();
      detached->source_file.reset();
      return Value{std::move(detached)};
    }
    if (name == "decl_name" || name == "record_name" || name == "parameter_name") {
      for (const auto* field : {"qualified_name", "identifier", "literal_operator_suffix"})
        if (auto text = nested_text(*value.message, field))
          return Value{std::move(*text)};
      return Value{};
    }
  }
  if (value.file_handle && descriptor == match::FileInfo::descriptor()) {
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
  if (descriptor == ctk::analysis::v1::BatchRun::descriptor()) {
    const auto& run = static_cast<const ctk::analysis::v1::BatchRun&>(*value.message);
    if (name == "status")
      return Value{run.state()};
    if (name == "results" || name == "result_group_indices") {
      std::vector<Value> results;
      for (const auto& group : run.groups()) {
        if (group.state() != "completed")
          continue;
        const ctk::analysis::v1::ScriptValue* final = nullptr;
        for (const auto& emission : group.result().emissions())
          if (emission.name() == "__final__")
            final = &emission.value();
        if (!final)
          continue;
        if (name == "results")
          results.push_back({std::make_shared<SemanticValue>(child(value, *final, "results"))});
        else
          results.push_back({static_cast<std::int64_t>(group.index())});
      }
      return list(std::move(results), true);
    }
  }
  if (descriptor == ctk::analysis::v1::ScriptValue::descriptor() && name == "kind") {
    const auto* field = value.message->GetReflection()->GetOneofFieldDescriptor(
        *value.message, descriptor->FindOneofByName("value"));
    return field ? Value{std::string(field->name())} : Value{};
  }
  if (value.selected && name == "binding")
    return Value{value.selected};
  if (value.graph_nodes && (name == "response" || name == "proto") &&
      value.message == value.owner.get()) {
    return Value{std::make_shared<SemanticValue>(value)};
  }
  if (descriptor == ast::AstNode::descriptor() &&
      (name == "name" || name == "qualified_name" || name == "declared_type")) {
    if (auto alias = node_alias(value, name))
      return std::move(*alias);
    return fail(llvm::Twine("AST node has no available ") + name + " convenience field");
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

namespace {

namespace graph_api = ctk::analysis::v1;
using NodeIndex = std::uint64_t;

bool unresolved(const graph_api::CallGraphCallSite& site) {
  if (site.has_callee_node())
    return false;
  if (!site.has_facts())
    return true;
  const auto& facts = site.facts();
  if (facts.dispatch() == match::CALL_DISPATCH_INDIRECT)
    return true;
  if (facts.dispatch() == match::CALL_DISPATCH_DIRECT ||
      facts.dispatch() == match::CALL_DISPATCH_VIRTUAL)
    return false;
  return facts.static_callee_symbol_identity().empty() && facts.static_callee_name().empty();
}

class GraphTopology {
public:
  explicit GraphTopology(const SemanticValue& value)
      : source(value), graph(static_cast<const graph_api::CallGraphResponse&>(*value.message)) {
    for (const auto& node : graph.nodes()) {
      if (node.is_virtual_root() || node.node_index() == graph.root_node())
        continue;
      nodes.emplace(node.node_index(), &node);
      incoming.try_emplace(node.node_index());
      outgoing.try_emplace(node.node_index());
    }
    for (const auto& edge : graph.edges()) {
      if (!nodes.contains(edge.caller_node()) || !nodes.contains(edge.callee_node()))
        continue;
      edges.push_back(&edge);
      outgoing[edge.caller_node()].push_back(edge.callee_node());
      incoming[edge.callee_node()].push_back(edge.caller_node());
    }
  }

  llvm::Expected<NodeIndex> select(const Value& target) const {
    if (const auto* index = as<std::int64_t>(target)) {
      if (*index >= 0 && nodes.contains(*index))
        return *index;
      return fail("call graph has no node at that index");
    }
    if (const auto* name = as<std::string>(target)) {
      auto found = semantic_method(source, "function", Sequence{{target}});
      if (!found)
        return found.takeError();
      return select(*found);
    }
    if (const auto* message = semantic_message(target)) {
      if (message->GetDescriptor() == graph_api::CallGraphNode::descriptor()) {
        const auto& selected = static_cast<const graph_api::CallGraphNode&>(*message);
        const auto item = nodes.find(selected.node_index());
        if (item != nodes.end() &&
            (item->second == &selected ||
             item->second->SerializeAsString() == selected.SerializeAsString()))
          return item->first;
        return fail("node does not belong to this call graph");
      }
    }
    if (retained_node(target)) {
      auto selected = semantic_method(source, "function", Sequence{{target}});
      if (!selected)
        return selected.takeError();
      return select(*selected);
    }
    return fail("target must be a node index, qualified name or call-graph node");
  }

  Value node(NodeIndex index) const {
    return {std::make_shared<SemanticValue>(child(source, *nodes.at(index), "nodes"))};
  }

  Value site(const graph_api::CallGraphCallSite& value) const {
    return {std::make_shared<SemanticValue>(child(source, value, "call_sites"))};
  }

  Value path(NodeIndex start, NodeIndex finish, bool route) const {
    std::map<NodeIndex, NodeIndex> parents{{start, start}};
    std::deque<NodeIndex> queue{start};
    while (!queue.empty() && !parents.contains(finish)) {
      const auto current = queue.front();
      queue.pop_front();
      for (const auto neighbor : outgoing.at(current)) {
        if (parents.emplace(neighbor, current).second)
          queue.push_back(neighbor);
      }
    }
    if (!parents.contains(finish))
      return {};
    std::vector<NodeIndex> steps;
    for (auto current = finish;; current = parents.at(current)) {
      steps.push_back(current);
      if (current == start)
        break;
    }
    std::reverse(steps.begin(), steps.end());
    std::vector<Value> result;
    if (!route) {
      for (const auto index : steps)
        result.push_back(node(index));
    } else {
      std::map<std::pair<NodeIndex, NodeIndex>, std::vector<Value>> sites;
      for (const auto& call : graph.call_sites())
        if (call.has_callee_node())
          sites[{call.caller_node(), call.callee_node()}].push_back(site(call));
      for (std::size_t i = 1; i < steps.size(); ++i) {
        auto item = std::make_shared<Record>();
        item->set("caller", node(steps[i - 1]));
        item->set("callee", node(steps[i]));
        item->set("call_sites", list(std::move(sites[{steps[i - 1], steps[i]}]), true));
        result.push_back({std::move(item)});
      }
    }
    return list(std::move(result), true);
  }

  Value grouped() const {
    using Key = std::pair<NodeIndex, std::optional<NodeIndex>>;
    std::map<Key, std::vector<const graph_api::CallGraphCallSite*>> groups;
    for (const auto& call : graph.call_sites()) {
      if (!nodes.contains(call.caller_node()))
        continue;
      const auto callee = call.has_callee_node() && nodes.contains(call.callee_node())
                              ? std::optional{call.callee_node()}
                              : std::nullopt;
      groups[{call.caller_node(), callee}].push_back(&call);
    }
    std::vector<Value> result;
    for (const auto& [key, calls] : groups) {
      auto item = std::make_shared<Record>();
      item->set("caller", node(key.first));
      item->set("callee", key.second ? node(*key.second) : Value{});
      item->set("call_site_count", {static_cast<std::int64_t>(calls.size())});
      std::int64_t unknown = 0;
      std::vector<Value> sites;
      for (const auto* call : calls) {
        unknown += unresolved(*call);
        sites.push_back(site(*call));
      }
      item->set("unresolved_count", {unknown});
      item->set("call_sites", list(std::move(sites), true));
      result.push_back({std::move(item)});
    }
    return list(std::move(result), true);
  }

  Value recursive() const {
    std::set<NodeIndex> seen;
    std::vector<NodeIndex> finished;
    for (const auto& [start, _] : nodes) {
      if (!seen.insert(start).second)
        continue;
      std::vector<std::pair<NodeIndex, std::size_t>> stack{{start, 0}};
      while (!stack.empty()) {
        auto& [current, offset] = stack.back();
        const auto& neighbors = outgoing.at(current);
        if (offset == neighbors.size()) {
          finished.push_back(current);
          stack.pop_back();
        } else {
          const auto next = neighbors[offset++];
          if (seen.insert(next).second)
            stack.emplace_back(next, 0);
        }
      }
    }
    seen.clear();
    std::vector<std::vector<NodeIndex>> components;
    for (const auto start : llvm::reverse(finished)) {
      if (!seen.insert(start).second)
        continue;
      std::vector<NodeIndex> component, stack{start};
      while (!stack.empty()) {
        const auto current = stack.back();
        stack.pop_back();
        component.push_back(current);
        for (const auto previous : incoming.at(current))
          if (seen.insert(previous).second)
            stack.push_back(previous);
      }
      if (component.size() > 1 || llvm::is_contained(outgoing.at(start), start)) {
        llvm::sort(component);
        components.push_back(std::move(component));
      }
    }
    llvm::sort(components);
    std::vector<Value> result;
    for (const auto& component : components) {
      std::vector<Value> members;
      for (const auto index : component)
        members.push_back(node(index));
      result.push_back(list(std::move(members), true));
    }
    return list(std::move(result), true);
  }

  Value neighborhood(NodeIndex start, std::optional<std::uint64_t> depth, bool reverse) const {
    std::map<NodeIndex, std::uint64_t> distances{{start, 0}};
    std::deque<NodeIndex> queue{start};
    const auto& adjacency = reverse ? incoming : outgoing;
    while (!queue.empty()) {
      const auto current = queue.front();
      queue.pop_front();
      const auto distance = distances.at(current);
      if (depth && distance == *depth)
        continue;
      for (const auto next : adjacency.at(current))
        if (distances.emplace(next, distance + 1).second)
          queue.push_back(next);
    }

    auto response = std::make_unique<graph_api::CallGraphResponse>(graph);
    response->clear_nodes();
    response->clear_edges();
    response->clear_call_sites();
    response->clear_availability();
    bool complete = true, known = true;
    auto copy = [&](const auto& item, auto* out) {
      *out = item;
      if (!item.has_is_complete())
        known = false;
      else
        complete &= item.is_complete();
      for (const auto& field : item.availability())
        *response->add_availability() = field;
    };
    std::map<NodeIndex, NodeIndex> remap;
    for (const auto& [index, _] : distances) {
      auto* out = response->add_nodes();
      copy(*nodes.at(index), out);
      out->set_node_index(remap.size());
      remap.emplace(index, out->node_index());
    }
    const auto within = [&](NodeIndex index) {
      return remap.contains(index) && (!depth || distances.at(index) < *depth);
    };
    std::uint64_t boundary_edges = 0, boundary_sites = 0;
    for (const auto* edge : edges) {
      const auto caller = edge->caller_node(), callee = edge->callee_node();
      if (remap.contains(caller) && remap.contains(callee) && within(reverse ? callee : caller)) {
        auto* out = response->add_edges();
        copy(*edge, out);
        out->set_caller_node(remap.at(caller));
        out->set_callee_node(remap.at(callee));
      } else if (remap.contains(caller) || remap.contains(callee))
        ++boundary_edges;
    }
    for (const auto& call : graph.call_sites()) {
      const auto caller = call.caller_node(), callee = call.callee_node();
      const bool caller_selected = remap.contains(caller);
      const bool callee_selected = call.has_callee_node() && remap.contains(callee);
      const bool keep = call.has_callee_node() ? caller_selected && callee_selected &&
                                                     within(reverse ? callee : caller)
                                               : !reverse && within(caller);
      if (keep) {
        auto* out = response->add_call_sites();
        copy(call, out);
        out->set_caller_node(remap.at(caller));
        if (callee_selected)
          out->set_callee_node(remap.at(callee));
      } else if (caller_selected || callee_selected)
        ++boundary_sites;
    }
    response->set_root_node(std::numeric_limits<NodeIndex>::max());
    response->set_focus_node(remap.at(start));
    response->set_selection_direction(reverse ? graph_api::CALL_GRAPH_DIRECTION_IN
                                              : graph_api::CALL_GRAPH_DIRECTION_OUT);
    if (depth) {
      response->set_selection_max_depth(*depth);
      response->clear_selection_unlimited_depth();
    } else {
      response->clear_selection_max_depth();
      response->set_selection_unlimited_depth(true);
    }
    response->set_selection_boundary_edges(graph.selection_boundary_edges() + boundary_edges);
    response->set_selection_boundary_call_sites(graph.selection_boundary_call_sites() +
                                                boundary_sites);
    if (known)
      response->set_is_complete(complete);
    else
      response->clear_is_complete();
    auto result = semantic(std::move(response));
    result->graph_nodes = source.graph_nodes;
    return {std::move(result)};
  }

private:
  const SemanticValue& source;
  const graph_api::CallGraphResponse& graph;
  std::map<NodeIndex, const graph_api::CallGraphNode*> nodes;
  std::map<NodeIndex, std::vector<NodeIndex>> incoming, outgoing;
  std::vector<const graph_api::CallGraphEdge*> edges;
};

llvm::Expected<Value> graph_method(const SemanticValue& view, llvm::StringRef name,
                                   const Sequence& arguments, Values* runtime) {
  const auto& args = arguments.items;
  GraphTopology topology(view);
  if (name == "grouped_calls" || name == "recursive_components" || name == "recursion_components") {
    if (!args.empty())
      return fail(llvm::Twine(name) + " takes no arguments");
    return name == "grouped_calls" ? topology.grouped() : topology.recursive();
  }
  if (name == "shortest_path" || name == "shortest_route") {
    if (args.size() != 2)
      return fail(llvm::Twine(name) + " requires source and target");
    auto start = topology.select(args[0]);
    if (!start)
      return start.takeError();
    auto end = topology.select(args[1]);
    if (!end)
      return end.takeError();
    return topology.path(*start, *end, name == "shortest_route");
  }
  if (args.empty() || args.size() > 2)
    return fail(llvm::Twine(name) + " requires a target and optional depth");
  std::optional<std::uint64_t> depth = 1;
  if (args.size() == 2) {
    if (const auto* value = as<std::int64_t>(args[1]); value && *value >= 0 && *value <= 32)
      depth = *value;
    else if (const auto* text = as<std::string>(args[1]); text && *text == "all")
      depth.reset();
    else
      return fail("depth must be 0..32 or 'all'");
  }
  if (const auto* target = object<NativeNode>(args[0]); runtime && target) {
    const auto& graph = static_cast<const graph_api::CallGraphResponse&>(*view.message);
    const auto* selected = select_callgraph(*runtime, *target, graph, depth, name == "callers");
    if (!selected)
      return fail(runtime->error);
    return *selected;
  }
  auto root = topology.select(args[0]);
  if (!root)
    return root.takeError();
  return topology.neighborhood(*root, depth, name == "callers");
}

} // namespace

llvm::Expected<Value> semantic_method(const SemanticValue& value, llvm::StringRef name,
                                      const Sequence& arguments, Values* runtime) {
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
  if (value.graph_nodes &&
      value.message->GetDescriptor() == ctk::analysis::v1::CallGraphResponse::descriptor() &&
      (name == "callers" || name == "callees" || name == "shortest_path" ||
       name == "shortest_route" || name == "grouped_calls" || name == "recursive_components" ||
       name == "recursion_components"))
    return graph_method(value, name, arguments, runtime);
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

llvm::json::Object semantic_preview_metadata(const SemanticValue& value) {
  llvm::json::Array availability;
  for (const auto* field : value.availability) {
    availability.push_back(llvm::json::Array{
        field->field_path(),
        field->has_state() ? llvm::json::Value(static_cast<int>(field->state())) : nullptr,
        field->has_reason() ? llvm::json::Value(field->reason()) : nullptr,
    });
  }
  return llvm::json::Object{{"path", value.path}, {"availability", std::move(availability)}};
}

llvm::Expected<llvm::json::Object> semantic_snapshot(const SemanticValue& value, llvm::StringRef only_field) {
  if (value.file_handle || value.message->GetDescriptor() == match::SessionInfo::descriptor())
    return fail("native resource handles cannot be saved");
  const pb::Message* message = value.message;
  std::unique_ptr<pb::Message> detached;
  if (message->GetDescriptor() == graph_api::CallGraphResponse::descriptor()) {
    auto copy = std::make_unique<graph_api::CallGraphResponse>(
        static_cast<const graph_api::CallGraphResponse&>(*message));
    copy->clear_retained_nodes();
    for (auto& node : *copy->mutable_nodes())
      node.clear_native_match_index();
    detached = std::move(copy);
  } else if (message->GetDescriptor() == graph_api::CallGraphNode::descriptor()) {
    auto copy = std::make_unique<graph_api::CallGraphNode>(
        static_cast<const graph_api::CallGraphNode&>(*message));
    copy->clear_native_match_index();
    detached = std::move(copy);
  }
  if (!only_field.empty()) {
    detached.reset(message->New());
    detached->CopyFrom(*message);
    for (int index = 0; index < message->GetDescriptor()->field_count(); ++index) {
      const auto* field = message->GetDescriptor()->field(index);
      if (llvm::StringRef(field->name()) != only_field)
        detached->GetReflection()->ClearField(detached.get(), field);
    }
  }
  if (detached)
    message = detached.get();
  pb::util::JsonPrintOptions options;
  options.preserve_proto_field_names = true;
  std::string json;
  const auto status = pb::util::MessageToJsonString(*message, &json, options);
  if (!status.ok())
    return fail(status.ToString());
  auto decoded = llvm::json::parse(json);
  if (!decoded)
    return decoded.takeError();
  if (!decoded->getAsObject())
    return fail("semantic snapshot requires a message object");
  auto result = semantic_preview_metadata(value);
  result["message_type"] = std::string(message->GetDescriptor()->full_name());
  result["message"] = std::move(*decoded);
  if (!only_field.empty())
    result["field"] = only_field;
  return result;
}

llvm::Expected<Value> restore_semantic_snapshot(const llvm::json::Object& snapshot) {
  const auto name = snapshot.getString("message_type");
  const auto path = snapshot.getString("path");
  const auto* availability = snapshot.getArray("availability");
  const auto* json = snapshot.getObject("message");
  if (!name || !path || !availability || !json)
    return fail("invalid semantic snapshot metadata");
  const auto* descriptor = pb::DescriptorPool::generated_pool()->FindMessageTypeByName(name->str());
  if (!descriptor)
    return fail("unknown semantic snapshot message type");
  const auto* prototype = pb::MessageFactory::generated_factory()->GetPrototype(descriptor);
  if (!prototype)
    return fail("semantic snapshot message is unavailable");
  std::unique_ptr<pb::Message> message(prototype->New());
  std::string wire;
  llvm::raw_string_ostream output(wire);
  output << llvm::json::Value(llvm::json::Object(*json));
  const auto parsed = pb::util::JsonStringToMessage(wire, message.get());
  if (!parsed.ok())
    return fail(parsed.ToString());
  auto entries = std::make_shared<std::vector<ast::FieldAvailability>>();
  entries->reserve(availability->size());
  for (const auto& item : *availability) {
    const auto* fields = item.getAsArray();
    if (!fields || fields->size() != 3)
      return fail("invalid semantic field availability");
    const auto field_path = (*fields)[0].getAsString();
    if (!field_path)
      return fail("invalid semantic availability path");
    auto& entry = entries->emplace_back();
    entry.set_field_path(field_path->str());
    if (const auto state = (*fields)[1].getAsInteger())
      entry.set_state(static_cast<ast::FieldState>(*state));
    if (const auto reason = (*fields)[2].getAsString())
      entry.set_reason(reason->str());
  }
  auto value = semantic(std::move(message));
  value->path = path->str();
  value->restored_availability = entries;
  value->availability.clear();
  for (const auto& entry : *entries)
    value->availability.push_back(&entry);
  if (const auto field = snapshot.getString("field"))
    return semantic_field(*value, *field);
  return Value{std::move(value)};
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
