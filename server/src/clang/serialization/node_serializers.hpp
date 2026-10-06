#pragma once

#include "ctk/clang/tooling.hpp"

#include <clang/AST/ASTContext.h>
#include <clang/AST/ASTTypeTraits.h>
#include <clang/AST/Decl.h>
#include <clang/AST/DeclCXX.h>
#include <clang/AST/DeclFriend.h>
#include <clang/AST/Expr.h>
#include <clang/AST/ExprConcepts.h>
#include <clang/AST/ExprCXX.h>
#include <clang/AST/Type.h>
#include <clang/Basic/Version.h>
#include <google/protobuf/message.h>

#include <functional>
#include <string>

namespace ctk::clang_layer::serialization {

struct SerializationContext {
  clang::ASTContext &ast_context;
  bool complete = false;
};

class SemanticFieldWriters final {
public:
  static void write(const clang::Decl &native, google::protobuf::Message &payload,
                    SerializationContext &context);
  static void write(const clang::Stmt &native, google::protobuf::Message &payload,
                    SerializationContext &context);
  static void write(const clang::Type &native, google::protobuf::Message &payload,
                    SerializationContext &context);

  static void write(const clang::FunctionDecl &native,
                    ctk::ast::v1::FunctionDecl &payload,
                    SerializationContext &context);
  static void write(const clang::VarDecl &native,
                    ctk::ast::v1::VarDecl &payload,
                    SerializationContext &context);
  static void write(const clang::IntegerLiteral &native,
                    ctk::ast::v1::IntegerLiteral &payload,
                    SerializationContext &context);
  static void write(const clang::StringLiteral &native,
                    ctk::ast::v1::StringLiteral &payload,
                    SerializationContext &context);
  static void write(const clang::CallExpr &native,
                    ctk::ast::v1::CallExpr &payload,
                    SerializationContext &context);
  static void write(const clang::CXXMemberCallExpr &native,
                    ctk::ast::v1::CXXMemberCallExpr &payload,
                    SerializationContext &context);

};

class NodeSerializer {
public:
  virtual ~NodeSerializer() = default;
  virtual bool serialize(const clang::DynTypedNode &node,
                         ctk::match::v1::MatchBinding &binding,
                         SerializationContext &context) const = 0;
};

#define CTK_AST_NODE(Type, field)                                               \
  class Type##Serializer final : public NodeSerializer {                        \
  public:                                                                        \
    bool serialize(const clang::DynTypedNode &node,                              \
                   ctk::match::v1::MatchBinding &binding,                        \
                   SerializationContext &context) const override {              \
      const auto *native = node.get<clang::Type>();                              \
      if (native == nullptr)                                                     \
        return false;                                                            \
      auto *payload = binding.mutable_node()->mutable_##field();                 \
      SemanticFieldWriters::write(*native, *payload, context);                   \
      binding.set_is_complete(context.complete);                                 \
      auto *availability = binding.add_availability();                          \
      availability->set_field_path("node-specific semantic fields");           \
      availability->set_state(                                                  \
          ctk::ast::v1::FIELD_STATE_UNAVAILABLE);                                \
      availability->set_reason(                                                  \
          "this serializer currently writes shared semantic fields only");     \
      if (node.get<clang::Decl>() != nullptr) {                                  \
        binding.add_supported_scopes(                                           \
            ctk::match::v1::BINDING_MATCH_SCOPE_ROOT_ONLY);                      \
        binding.add_supported_scopes(                                           \
            ctk::match::v1::BINDING_MATCH_SCOPE_SUBTREE);                        \
      } else if (node.get<clang::Stmt>() != nullptr) {                           \
        binding.add_supported_scopes(                                           \
            ctk::match::v1::BINDING_MATCH_SCOPE_ROOT_ONLY);                      \
        binding.add_supported_scopes(                                           \
            ctk::match::v1::BINDING_MATCH_SCOPE_SUBTREE);                        \
      } else if (node.get<clang::Type>() != nullptr) {                            \
        binding.add_supported_scopes(                                           \
            ctk::match::v1::BINDING_MATCH_SCOPE_ROOT_ONLY);                      \
      }                                                                          \
      return true;                                                               \
    }                                                                            \
  };

#define CTK_AST_NODE_DECL(Type, field) CTK_AST_NODE(Type, field);
#define CTK_AST_NODE_STMT(Type, field) CTK_AST_NODE(Type, field);
#define CTK_AST_NODE_EXPR(Type, field) CTK_AST_NODE(Type, field);
#define CTK_AST_NODE_TYPE(Type, field) CTK_AST_NODE(Type, field);
#include "node_serializer_catalog.inc"
#undef CTK_AST_NODE_TYPE
#undef CTK_AST_NODE_EXPR
#undef CTK_AST_NODE_STMT
#undef CTK_AST_NODE_DECL
#undef CTK_AST_NODE

class NodeSerializerDispatcher final {
public:
  static bool serialize(const clang::DynTypedNode &node,
                        ctk::match::v1::MatchBinding &binding,
                        SerializationContext &context);
};

} // namespace ctk::clang_layer::serialization
