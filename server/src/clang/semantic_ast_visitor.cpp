#include "semantic_ast_visitor.hpp"
#include "serialization/analysis_projection.hpp"
#include "serialization/node_serializers.hpp"
#include <algorithm>
#include <clang/Basic/SourceManager.h>
#include <llvm/Config/llvm-config.h>

namespace ctk::clang_layer {
SemanticAstVisitor::SemanticAstVisitor(
    clang::ASTContext &context,
    const ctk::analysis::v1::TraverseRequest &request,
    const IMatchBackend::Checkpoint &checkpoint, const TraversalLimits &limits,
    TraversalResult &result, const ITraversalBackend::NodeSink &sink)
    : context_(context), request_(request), checkpoint_(checkpoint),
      limits_(limits), result_(result), sink_(sink) {}
bool SemanticAstVisitor::shouldVisitImplicitCode() const {
  return request_.visit_implicit_code();
}
bool SemanticAstVisitor::shouldVisitTemplateInstantiations() const {
  return request_.visit_template_instantiations();
}
bool SemanticAstVisitor::enter(const clang::DynTypedNode &node, bool leaf) {
  if (result_.code != MatchCode::Ok)
    return false;
  if (!checkpoint_()) {
    result_.code = MatchCode::Cancelled;
    result_.message = "AST traversal cancelled";
    return false;
  }
  const auto depth = request_.has_max_depth() ? request_.max_depth() : 64U;
  if (parents_.size() > depth) {
    result_.response.set_depth_limited(true);
    return false;
  }
  const auto maximum = request_.has_max_nodes() ? request_.max_nodes() : 10000U;
  if (static_cast<std::size_t>(result_.node_count) >=
      std::min<std::size_t>(maximum, limits_.max_nodes)) {
    result_.code = MatchCode::ResourceExhausted;
    result_.message = "AST traversal node limit exceeded";
    return false;
  }
  ctk::analysis::v1::TraversalNode record;
  record.set_index(result_.node_count);
  record.set_native_kind(node.getNodeKind().asStringRef().str());
  record.set_leaf(leaf);
  record.set_depth(parents_.size());
  if (!parents_.empty())
    record.set_parent_index(parents_.back());
  serialization::SerializationContext context{context_};
  serialization::apply_projection(request_.projection(), context);
  if (!serialization::NodeSerializerDispatcher::serialize(
          node, *record.mutable_value(), context) &&
      !record.value().has_unsupported()) {
    result_.code = MatchCode::Internal;
    result_.message = "AST traversal node serialization failed";
    return false;
  }
  const auto bytes = record.ByteSizeLong();
  const auto overhead = sink_ ? 16U : 0U;
  if (overhead > limits_.max_bytes || bytes > limits_.max_bytes - overhead ||
      (!sink_ && bytes > limits_.max_bytes - bytes_)) {
    result_.code = MatchCode::ResourceExhausted;
    result_.message = "AST traversal response limit exceeded";
    return false;
  }
  if (sink_) {
    result_.code = sink_(record, result_.message);
    if (result_.code != MatchCode::Ok)
      return false;
  } else {
    bytes_ += bytes;
    result_.response.add_nodes()->CopyFrom(record);
  }
  parents_.push_back(result_.node_count++);
  return true;
}
bool SemanticAstVisitor::TraverseDecl(clang::Decl *declaration) {
  if (!declaration)
    return true;
  const auto &sources = context_.getSourceManager();
  if (!explicit_root_ && request_.main_file_only() &&
      !llvm::isa<clang::TranslationUnitDecl>(declaration) &&
      declaration->getLocation().isValid() &&
      !sources.isWrittenInMainFile(
          sources.getExpansionLoc(declaration->getLocation())))
    return true;
  // Native RAV still visits explicit constraints on implicit template
  // parameters.
  if (!explicit_root_ && declaration->isImplicit() &&
      !shouldVisitImplicitCode())
    return clang::RecursiveASTVisitor<SemanticAstVisitor>::TraverseDecl(
        declaration);
  if (!enter(clang::DynTypedNode::create(*declaration)))
    return result_.code == MatchCode::Ok;
  explicit_root_ = false;
  const bool success = Base::TraverseDecl(declaration);
  parents_.pop_back();
  return success;
}
bool SemanticAstVisitor::dataTraverseStmtPre(clang::Stmt *statement) {
  const auto &sources = context_.getSourceManager();
  if (!explicit_root_ && request_.main_file_only() &&
      statement->getBeginLoc().isValid() &&
      !sources.isWrittenInMainFile(
          sources.getExpansionLoc(statement->getBeginLoc())))
    return false;
  explicit_root_ = false;
  return enter(clang::DynTypedNode::create(*statement));
}
bool SemanticAstVisitor::dataTraverseStmtPost(clang::Stmt *) {
  parents_.pop_back();
  return result_.code == MatchCode::Ok;
}
// Each native entry point owns one preorder frame. Traversal edges are RAV
// syntax edges, not declaration references (e.g. a record type is not its
// decl).
bool SemanticAstVisitor::around(const clang::DynTypedNode &node,
                                const std::function<bool()> &visit, bool leaf) {
  explicit_root_ = false;
  if (!enter(node, leaf))
    return result_.code == MatchCode::Ok;
  const bool complete = visit();
  parents_.pop_back();
  return complete && result_.code == MatchCode::Ok;
}
namespace {
template <class Visitor>
bool traverse_type(Visitor &visitor, clang::QualType type, bool qualifier) {
  if constexpr (requires { visitor.TraverseType(type, qualifier); })
    return visitor.TraverseType(type, qualifier);
  else
    return visitor.TraverseType(type);
}
template <class Visitor>
bool traverse_type_loc(Visitor &visitor, clang::TypeLoc loc, bool qualifier) {
  if constexpr (requires { visitor.TraverseTypeLoc(loc, qualifier); })
    return visitor.TraverseTypeLoc(loc, qualifier);
  else
    return visitor.TraverseTypeLoc(loc);
}
} // namespace
bool SemanticAstVisitor::TraverseType(clang::QualType type, bool qualifier) {
  if (type.isNull())
    return true;
  return around(clang::DynTypedNode::create(type), [&] {
    return traverse_type(static_cast<Base &>(*this), type, qualifier);
  });
}
bool SemanticAstVisitor::TraverseTypeLoc(clang::TypeLoc loc, bool qualifier) {
  if (loc.isNull())
    return true;
  return around(clang::DynTypedNode::create(loc), [&] {
    return traverse_type_loc(static_cast<Base &>(*this), loc, qualifier);
  });
}
bool SemanticAstVisitor::TraverseAttr(clang::Attr *attr) {
  if (!attr)
    return true;
  return around(clang::DynTypedNode::create(*attr),
                [&] { return Base::TraverseAttr(attr); });
}
namespace {
template <class T> clang::DynTypedNode native_node(T value) {
  if constexpr (std::is_pointer_v<T>)
    return clang::DynTypedNode::create(*value);
  else
    return clang::DynTypedNode::create(value);
}
template <class T> bool valid_nns(T value) {
  if constexpr (std::is_pointer_v<T>)
    return value != nullptr;
  else
    return value.getKind() != T::Kind::Null;
}
template <class T> T native_nns(const clang::NestedNameSpecifier *value) {
  if constexpr (std::is_pointer_v<T>)
    return const_cast<clang::NestedNameSpecifier *>(value);
  else
    return *value;
}
} // namespace
bool SemanticAstVisitor::TraverseNestedNameSpecifier(NativeNNS nns) {
  if (!valid_nns(nns))
    return true;
  return around(native_node(nns),
                [&] { return Base::TraverseNestedNameSpecifier(nns); });
}
bool SemanticAstVisitor::TraverseNestedNameSpecifierLoc(
    clang::NestedNameSpecifierLoc loc) {
  if (!loc)
    return true;
  return around(clang::DynTypedNode::create(loc),
                [&] { return Base::TraverseNestedNameSpecifierLoc(loc); });
}
bool SemanticAstVisitor::TraverseTemplateArgument(
    const clang::TemplateArgument &arg) {
  return around(clang::DynTypedNode::create(arg),
                [&] { return Base::TraverseTemplateArgument(arg); });
}
bool SemanticAstVisitor::TraverseTemplateArgumentLoc(
    const clang::TemplateArgumentLoc &loc) {
  return around(clang::DynTypedNode::create(loc),
                [&] { return Base::TraverseTemplateArgumentLoc(loc); });
}
bool SemanticAstVisitor::TraverseTemplateName(clang::TemplateName name) {
  if (name.isNull())
    return true;
  return around(clang::DynTypedNode::create(name),
                [&] { return Base::TraverseTemplateName(name); });
}
bool SemanticAstVisitor::TraverseCXXBaseSpecifier(
    const clang::CXXBaseSpecifier &base) {
  return around(clang::DynTypedNode::create(base),
                [&] { return Base::TraverseCXXBaseSpecifier(base); });
}
bool SemanticAstVisitor::TraverseConstructorInitializer(
    clang::CXXCtorInitializer *init) {
  if (!init)
    return true;
  return around(clang::DynTypedNode::create(*init),
                [&] { return Base::TraverseConstructorInitializer(init); });
}
bool SemanticAstVisitor::TraverseOMPClause(clang::OMPClause *clause) {
  if (!clause)
    return true;
  return around(clang::DynTypedNode::create(*clause), [&] {
    for (auto *child : clause->children())
      if (!TraverseStmt(child))
        return false;
    return true;
  });
}
bool SemanticAstVisitor::traverse_node(const clang::DynTypedNode &node) {
  explicit_root_ = true;
  if (auto *decl = node.get<clang::Decl>())
    return TraverseDecl(const_cast<clang::Decl *>(decl));
  if (auto *stmt = node.get<clang::Stmt>())
    return TraverseStmt(const_cast<clang::Stmt *>(stmt));
  if (auto *type = node.get<clang::Type>())
    return around(node,
                  [&] { return Base::TraverseType(clang::QualType(type, 0)); });
  if (auto *type = node.get<clang::QualType>())
    return TraverseType(*type);
  if (auto *loc = node.get<clang::TypeLoc>())
    return TraverseTypeLoc(*loc);
  if (auto *attr = node.get<clang::Attr>())
    return TraverseAttr(const_cast<clang::Attr *>(attr));
  if (auto *nns = node.get<clang::NestedNameSpecifier>())
    return TraverseNestedNameSpecifier(native_nns<NativeNNS>(nns));
  if (auto *loc = node.get<clang::NestedNameSpecifierLoc>())
    return TraverseNestedNameSpecifierLoc(*loc);
  if (auto *arg = node.get<clang::TemplateArgument>())
    return TraverseTemplateArgument(*arg);
  if (auto *arg = node.get<clang::TemplateArgumentLoc>())
    return TraverseTemplateArgumentLoc(*arg);
  if (auto *name = node.get<clang::TemplateName>())
    return TraverseTemplateName(*name);
  if (auto *base = node.get<clang::CXXBaseSpecifier>())
    return TraverseCXXBaseSpecifier(*base);
  if (auto *init = node.get<clang::CXXCtorInitializer>())
    return TraverseConstructorInitializer(
        const_cast<clang::CXXCtorInitializer *>(init));
  if (auto *clause = node.get<clang::OMPClause>())
    return TraverseOMPClause(const_cast<clang::OMPClause *>(clause));
#if LLVM_VERSION_MAJOR >= 18
  if (auto *ref = node.get<clang::ConceptReference>())
    return around(node, [&] {
      return Base::TraverseConceptReference(
          const_cast<clang::ConceptReference *>(ref));
    });
#endif
#if LLVM_VERSION_MAJOR >= 18
  if (auto *loc = node.get<clang::ObjCProtocolLoc>())
    return around(node, [&] { return Base::TraverseObjCProtocolLoc(*loc); });
#endif
  // Native auxiliary values needing enclosing context have no independent
  // RAV entry point. Preserve the selected node explicitly as a leaf.
  return around(node, [] { return true; }, true);
}
} // namespace ctk::clang_layer
