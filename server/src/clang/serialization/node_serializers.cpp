#include "node_serializers.hpp"

#include "ast/v1/record_type.pb.h"

#include <llvm/ADT/SmallString.h>

#include <algorithm>
#include <deque>
#include <type_traits>
#include <unordered_set>
#include <vector>

namespace ctk::clang_layer::serialization {
namespace {

using google::protobuf::Descriptor;
using google::protobuf::Message;

Message *find_message(Message &root, const std::string &name) {
  using Path = std::vector<const google::protobuf::FieldDescriptor *>;
  std::deque<std::pair<const Descriptor *, Path>> pending;
  std::unordered_set<const Descriptor *> visited;
  pending.emplace_back(root.GetDescriptor(), Path{});
  while (!pending.empty()) {
    auto [descriptor, path] = std::move(pending.front());
    pending.pop_front();
    if (!visited.insert(descriptor).second)
      continue;
    if (descriptor->name() == name) {
      Message *message = &root;
      for (const auto *field : path)
        message = message->GetReflection()->MutableMessage(message, field);
      return message;
    }
    if (path.size() >= 10)
      continue;
    for (int index = 0; index < descriptor->field_count(); ++index) {
      const auto *field = descriptor->field(index);
      if (field->cpp_type() !=
              google::protobuf::FieldDescriptor::CPPTYPE_MESSAGE ||
          field->is_repeated())
        continue;
      auto next_path = path;
      next_path.push_back(field);
      pending.emplace_back(field->message_type(), std::move(next_path));
    }
  }
  return nullptr;
}

void set_optional_bool(Message &message, const char *name, bool value) {
  const auto *field = message.GetDescriptor()->FindFieldByName(name);
  if (field == nullptr ||
      field->cpp_type() != google::protobuf::FieldDescriptor::CPPTYPE_BOOL ||
      !field->has_presence())
    return;
  message.GetReflection()->SetBool(&message, field, value);
}

void set_optional_string(Message &message, const char *name,
                         const std::string &value) {
  const auto *field = message.GetDescriptor()->FindFieldByName(name);
  if (field == nullptr ||
      field->cpp_type() != google::protobuf::FieldDescriptor::CPPTYPE_STRING ||
      !field->has_presence())
    return;
  message.GetReflection()->SetString(&message, field, value);
}

void set_name(Message &payload, const clang::NamedDecl &native) {
  auto *named = find_message(payload, "NamedDeclInfo");
  if (named == nullptr)
    return;
  auto *name = find_message(*named, "DeclarationName");
  if (name != nullptr && native.getIdentifier() != nullptr) {
    const auto *field = name->GetDescriptor()->FindFieldByName("identifier");
    name->GetReflection()->SetString(name, field, native.getNameAsString());
  }
  set_optional_string(*named, "qualified_name",
                      native.getQualifiedNameAsString());
}

void set_decl_flags(Message &payload, const clang::Decl &native) {
  if (auto *decl = find_message(payload, "DeclInfo")) {
    set_optional_bool(*decl, "is_implicit", native.isImplicit());
    set_optional_bool(*decl, "is_invalid", native.isInvalidDecl());
  }
}

void set_expr_flags(Message &payload, const clang::Expr &native) {
  if (auto *expr = find_message(payload, "ExprInfo")) {
    const auto *descriptor = expr->GetDescriptor();
    const auto *reflection = expr->GetReflection();
    const auto set_enum = [&](const char *field_name, const char *value_name) {
      const auto *field = descriptor->FindFieldByName(field_name);
      if (field == nullptr ||
          field->cpp_type() != google::protobuf::FieldDescriptor::CPPTYPE_ENUM)
        return;
      const auto *value = field->enum_type()->FindValueByName(value_name);
      if (value != nullptr)
        reflection->SetEnum(expr, field, value);
    };
    switch (native.getValueKind()) {
    case clang::VK_PRValue:
      set_enum("value_category", "VALUE_CATEGORY_PRVALUE");
      break;
    case clang::VK_LValue:
      set_enum("value_category", "VALUE_CATEGORY_LVALUE");
      break;
    case clang::VK_XValue:
      set_enum("value_category", "VALUE_CATEGORY_XVALUE");
      break;
    }
    switch (native.getObjectKind()) {
    case clang::OK_Ordinary:
      set_enum("object_kind", "OBJECT_KIND_ORDINARY");
      break;
    case clang::OK_BitField:
      set_enum("object_kind", "OBJECT_KIND_BIT_FIELD");
      break;
    case clang::OK_VectorComponent:
      set_enum("object_kind", "OBJECT_KIND_VECTOR_COMPONENT");
      break;
    case clang::OK_MatrixComponent:
      set_enum("object_kind", "OBJECT_KIND_MATRIX_COMPONENT");
      break;
    case clang::OK_ObjCProperty:
    case clang::OK_ObjCSubscript:
      break;
    }
    set_optional_bool(*expr, "is_type_dependent", native.isTypeDependent());
    set_optional_bool(*expr, "is_value_dependent", native.isValueDependent());
    set_optional_bool(*expr, "is_instantiation_dependent",
                      native.isInstantiationDependent());
    set_optional_bool(*expr, "contains_unexpanded_parameter_pack",
                      native.containsUnexpandedParameterPack());
    set_optional_bool(*expr, "contains_errors", native.containsErrors());
  }
}

void set_symbol(Message &symbol, const clang::NamedDecl &native,
                const clang::ASTContext &context) {
  (void)context;
  set_optional_string(symbol, "name", native.getNameAsString());
  set_optional_string(symbol, "qualified_name",
                      native.getQualifiedNameAsString());
  const auto *kind_field = symbol.GetDescriptor()->FindFieldByName("kind");
  if (kind_field != nullptr &&
      kind_field->cpp_type() ==
          google::protobuf::FieldDescriptor::CPPTYPE_ENUM) {
    const char *kind = "SYMBOL_KIND_OTHER";
    if (llvm::isa<clang::CXXConstructorDecl>(native))
      kind = "SYMBOL_KIND_CONSTRUCTOR";
    else if (llvm::isa<clang::CXXDestructorDecl>(native))
      kind = "SYMBOL_KIND_DESTRUCTOR";
    else if (llvm::isa<clang::CXXMethodDecl>(native))
      kind = "SYMBOL_KIND_METHOD";
    else if (llvm::isa<clang::FunctionDecl>(native))
      kind = "SYMBOL_KIND_FUNCTION";
    else if (llvm::isa<clang::RecordDecl>(native))
      kind = "SYMBOL_KIND_RECORD";
    else if (llvm::isa<clang::EnumDecl>(native))
      kind = "SYMBOL_KIND_ENUM";
    else if (llvm::isa<clang::NamespaceDecl>(native))
      kind = "SYMBOL_KIND_NAMESPACE";
    else if (llvm::isa<clang::FieldDecl>(native))
      kind = "SYMBOL_KIND_FIELD";
    else if (llvm::isa<clang::ParmVarDecl>(native))
      kind = "SYMBOL_KIND_PARAMETER";
    else if (llvm::isa<clang::VarDecl>(native))
      kind = "SYMBOL_KIND_VARIABLE";
    if (const auto *enum_value = kind_field->enum_type()->FindValueByName(kind))
      symbol.GetReflection()->SetEnum(&symbol, kind_field, enum_value);
  }
  if (auto *description = find_message(symbol, "TypeDescription")) {
    if (const auto *value = llvm::dyn_cast<clang::ValueDecl>(&native)) {
      const auto type = value->getType();
      set_optional_string(*description, "spelling", type.getAsString());
      set_optional_string(*description, "canonical_spelling",
                          type.getCanonicalType().getAsString());
    } else if (const auto *function =
                   llvm::dyn_cast<clang::FunctionDecl>(&native)) {
      const auto type = function->getType();
      set_optional_string(*description, "spelling", type.getAsString());
      set_optional_string(*description, "canonical_spelling",
                          type.getCanonicalType().getAsString());
    }
  }
}

void pack_any(const Message &payload, Message &any) {
  const auto type_url = std::string("type.googleapis.com/") +
                        std::string(payload.GetDescriptor()->full_name());
  const auto *type_url_field = any.GetDescriptor()->FindFieldByName("type_url");
  if (type_url_field != nullptr)
    any.GetReflection()->SetString(&any, type_url_field, type_url);
  const auto *bytes_field = any.GetDescriptor()->FindFieldByName("value");
  if (bytes_field != nullptr)
    any.GetReflection()->SetString(&any, bytes_field,
                                   payload.SerializeAsString());
}

void write_node_any(const clang::DynTypedNode &native, Message &any,
                    SerializationContext &context) {
  ctk::match::v1::MatchBinding binding;
  if (!NodeSerializerDispatcher::serialize(native, binding, context) ||
      !binding.has_node()) {
    if (binding.has_unsupported())
      pack_any(binding.unsupported(), any);
    return;
  }
  const auto &node = binding.node();
  const auto *oneof = node.GetDescriptor()->FindOneofByName("payload");
  const auto *payload_field =
      node.GetReflection()->GetOneofFieldDescriptor(node, oneof);
  if (payload_field == nullptr)
    return;
  const auto &payload = node.GetReflection()->GetMessage(node, payload_field);
  pack_any(payload, any);
}

void write_expression_value(const clang::Expr &native, Message &value,
                            SerializationContext &context) {
  set_optional_bool(value, "is_complete", false);
  if (auto *any = find_message(value, "Any"))
    write_node_any(clang::DynTypedNode::create(native), *any, context);
}

void write_qual_type(clang::QualType native, Message &value,
                     SerializationContext &context) {
  if (native.isNull())
    return;
  auto *type_value = find_message(value, "TypeValue");
  if (type_value == nullptr)
    return;
  const auto *field = type_value->GetDescriptor()->FindFieldByName("node");
  if (field == nullptr)
    return;
  auto *any = type_value->GetReflection()->MutableMessage(type_value, field);
  if (const auto *record =
          llvm::dyn_cast<clang::RecordType>(native.getTypePtr())) {
    ctk::ast::v1::RecordType payload;
    auto *info = payload.mutable_info();
    set_optional_string(*info, "spelling", native.getAsString());
    set_optional_string(*info, "canonical_spelling",
                        native.getCanonicalType().getAsString());
    set_optional_bool(*info, "is_dependent", record->isDependentType());
    if (record->getDecl() != nullptr)
      set_symbol(*payload.mutable_declaration(), *record->getDecl(),
                 context.ast_context);
    pack_any(payload, *any);
    return;
  }
  write_node_any(clang::DynTypedNode::create(*native.getTypePtr()), *any,
                 context);
}

void write_call_fields(const clang::CallExpr &native, Message &payload,
                       SerializationContext &context) {
  if (auto *info = find_message(payload, "CallExprInfo")) {
    const auto *callee_field =
        info->GetDescriptor()->FindFieldByName("callee_expression");
    if (callee_field != nullptr)
      write_expression_value(
          *native.getCallee(),
          *info->GetReflection()->MutableMessage(info, callee_field), context);
    if (const auto *callee = native.getDirectCallee()) {
      const auto *field =
          info->GetDescriptor()->FindFieldByName("direct_callee");
      if (field != nullptr)
        set_symbol(*info->GetReflection()->MutableMessage(info, field), *callee,
                   context.ast_context);
    }
    const auto *arguments = info->GetDescriptor()->FindFieldByName("arguments");
    if (arguments != nullptr) {
      for (const auto *argument : native.arguments()) {
        auto *slot = info->GetReflection()->AddMessage(info, arguments);
        write_expression_value(*argument, *slot, context);
      }
    }
  }
}

std::string apint_little_endian(const llvm::APInt &integer) {
  std::string bytes;
  bytes.reserve((integer.getBitWidth() + 7U) / 8U);
  for (unsigned bit = 0; bit < integer.getBitWidth(); bit += 8) {
    const auto width = std::min(8U, integer.getBitWidth() - bit);
    bytes.push_back(
        static_cast<char>(integer.extractBitsAsZExtValue(width, bit)));
  }
  return bytes;
}

template <class Serializer>
bool try_serialize(const clang::DynTypedNode &node,
                   ctk::match::v1::MatchBinding &binding,
                   SerializationContext &context) {
  static const Serializer serializer;
  return serializer.serialize(node, binding, context);
}

} // namespace

void SemanticFieldWriters::write(const clang::Decl &native, Message &payload,
                                 SerializationContext &) {
  if (const auto *named = llvm::dyn_cast<clang::NamedDecl>(&native))
    set_name(payload, *named);
  set_decl_flags(payload, native);
}

void SemanticFieldWriters::write(const clang::Stmt &native, Message &payload,
                                 SerializationContext &) {
  if (const auto *expression = llvm::dyn_cast<clang::Expr>(&native))
    set_expr_flags(payload, *expression);
}

void SemanticFieldWriters::write(const clang::Type &, Message &,
                                 SerializationContext &) {}

void SemanticFieldWriters::write(const clang::FunctionDecl &native,
                                 ctk::ast::v1::FunctionDecl &payload,
                                 SerializationContext &context) {
  write(static_cast<const clang::Decl &>(native), payload, context);
  auto *function = payload.mutable_function();
  set_optional_bool(*function, "is_this_declaration_a_definition",
                    native.isThisDeclarationADefinition());
  set_optional_bool(*function, "is_variadic", native.isVariadic());
  set_optional_bool(*function, "is_constexpr", native.isConstexpr());
  payload.set_is_deleted(native.isDeleted());
  payload.set_is_defaulted(native.isDefaulted());
  payload.set_is_explicitly_defaulted(native.isExplicitlyDefaulted());
  payload.set_is_pure_virtual(native.isPureVirtual());
  payload.set_is_trivial(native.isTrivial());
  payload.set_is_trivial_for_call(native.isTrivialForCall());
  payload.set_is_inline_specified(native.isInlineSpecified());
  context.complete = false;
}

void SemanticFieldWriters::write(const clang::VarDecl &native,
                                 ctk::ast::v1::VarDecl &payload,
                                 SerializationContext &context) {
  write(static_cast<const clang::Decl &>(native), payload, context);
  auto *variable = payload.mutable_variable();
  set_optional_bool(*variable, "is_constexpr", native.isConstexpr());
  context.complete = false;
}

void SemanticFieldWriters::write(const clang::IntegerLiteral &native,
                                 ctk::ast::v1::IntegerLiteral &payload,
                                 SerializationContext &context) {
  write(static_cast<const clang::Stmt &>(native), payload, context);
  const auto &value = native.getValue();
  auto *bits = payload.mutable_value();
  bits->set_bit_width(value.getBitWidth());
  bits->set_little_endian_bits(apint_little_endian(value));
  llvm::SmallString<64> decimal;
  value.toString(decimal, 10, false);
  bits->set_unsigned_decimal(decimal.str().str());
  context.complete = false;
}

void SemanticFieldWriters::write(const clang::StringLiteral &native,
                                 ctk::ast::v1::StringLiteral &payload,
                                 SerializationContext &context) {
  write(static_cast<const clang::Stmt &>(native), payload, context);
  payload.set_value(native.getBytes().str());
  payload.set_code_unit_width(native.getCharByteWidth() * 8U);
  payload.set_code_unit_count(native.getLength());
  context.complete = false;
}

void SemanticFieldWriters::write(const clang::CallExpr &native,
                                 ctk::ast::v1::CallExpr &payload,
                                 SerializationContext &context) {
  write(static_cast<const clang::Stmt &>(native), payload, context);
  write_call_fields(native, *payload.mutable_call(), context);
  context.complete = false;
}

void SemanticFieldWriters::write(const clang::CXXMemberCallExpr &native,
                                 ctk::ast::v1::CXXMemberCallExpr &payload,
                                 SerializationContext &context) {
  write(static_cast<const clang::Stmt &>(native), payload, context);
  write_call_fields(static_cast<const clang::CallExpr &>(native), payload,
                    context);
  const auto object_type_field =
      payload.GetDescriptor()->FindFieldByName("object_type");
  if (object_type_field != nullptr)
    write_qual_type(
        native.getObjectType(),
        *payload.GetReflection()->MutableMessage(&payload, object_type_field),
        context);
  if (const auto *object = native.getImplicitObjectArgument()) {
    const auto *field =
        payload.GetDescriptor()->FindFieldByName("implicit_object_argument");
    if (field != nullptr)
      write_expression_value(
          *object, *payload.GetReflection()->MutableMessage(&payload, field),
          context);
  }
  if (const auto *method = native.getMethodDecl()) {
    const auto *method_field =
        payload.GetDescriptor()->FindFieldByName("method_declaration");
    if (method_field != nullptr)
      set_symbol(
          *payload.GetReflection()->MutableMessage(&payload, method_field),
          *method, context.ast_context);
    if (const auto *record = method->getParent()) {
      const auto *record_field =
          payload.GetDescriptor()->FindFieldByName("record_declaration");
      if (record_field != nullptr)
        set_symbol(
            *payload.GetReflection()->MutableMessage(&payload, record_field),
            *record, context.ast_context);
    }
  }
  context.complete = false;
}

bool NodeSerializerDispatcher::serialize(const clang::DynTypedNode &node,
                                         ctk::match::v1::MatchBinding &binding,
                                         SerializationContext &context) {
  const auto kind = node.getNodeKind().asStringRef();
#define CTK_AST_NODE(Type, field)                                              \
  if (kind == #Type)                                                           \
    return try_serialize<Type##Serializer>(node, binding, context);
#define CTK_AST_NODE_DECL(Type, field) CTK_AST_NODE(Type, field)
#define CTK_AST_NODE_STMT(Type, field) CTK_AST_NODE(Type, field)
#define CTK_AST_NODE_EXPR(Type, field) CTK_AST_NODE(Type, field)
#define CTK_AST_NODE_TYPE(Type, field) CTK_AST_NODE(Type, field)
#include "node_serializer_catalog.inc"
#undef CTK_AST_NODE_TYPE
#undef CTK_AST_NODE_EXPR
#undef CTK_AST_NODE_STMT
#undef CTK_AST_NODE_DECL
#undef CTK_AST_NODE
  auto *unsupported = binding.mutable_unsupported();
  unsupported->set_clang_kind(kind.str());
  unsupported->set_clang_class(kind.str());
  unsupported->set_reason(ctk::ast::v1::UNSUPPORTED_REASON_DEFERRED_CONTRACT);
  unsupported->set_detail("no concrete AST node serializer was selected");
  binding.set_is_complete(false);
  return false;
}

} // namespace ctk::clang_layer::serialization
