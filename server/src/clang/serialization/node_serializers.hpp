#pragma once

#include "ctk/clang/tooling.hpp"
#include <clang/AST/ASTContext.h>
#include <clang/AST/ASTTypeTraits.h>
#include <clang/AST/Decl.h>
#include <clang/AST/DeclCXX.h>
#include <clang/AST/DeclFriend.h>
#include <clang/AST/DeclTemplate.h>
#include <clang/AST/Expr.h>
#include <clang/AST/ExprCXX.h>
#include <clang/AST/ExprConcepts.h>
#include <clang/AST/StmtCXX.h>
#include <clang/AST/Type.h>
#include <clang/Basic/Version.h>
#include <cstddef>
#include <google/protobuf/message.h>
#include <string>
#include <vector>

namespace ctk::clang_layer::serialization {

enum class ProjectionPolicy { Shallow, Recursive };

// The caller pins the AST and holds its execution lane throughout
// serialization. Output owns its data. Limits bound recursive owned children,
// never symbols.
struct SerializationContext {
  clang::ASTContext &ast_context;
  ProjectionPolicy projection = ProjectionPolicy::Recursive;
  bool complete = true;
  std::size_t depth = 0;
  std::size_t nodes = 0;
  std::size_t max_depth = 24;
  std::size_t max_nodes = 10000;
  std::vector<ctk::ast::v1::FieldAvailability> availability;
  std::vector<std::size_t> availability_starts;
};

class NodeSerializer {
public:
  virtual ~NodeSerializer() = default;
  virtual bool serialize(const clang::DynTypedNode &node,
                         ctk::match::v1::MatchBinding &binding,
                         SerializationContext &context) const = 0;
};

class NodeSerializerDispatcher final {
public:
  static bool serialize(const clang::DynTypedNode &node,
                        ctk::match::v1::MatchBinding &binding,
                        SerializationContext &context);
};

} // namespace ctk::clang_layer::serialization
