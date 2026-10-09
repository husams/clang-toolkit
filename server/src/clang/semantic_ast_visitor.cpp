#include "semantic_ast_visitor.hpp"
#include "serialization/node_serializers.hpp"
#include "serialization/analysis_projection.hpp"
#include <clang/Basic/SourceManager.h>
#include <algorithm>

namespace ctk::clang_layer {
SemanticAstVisitor::SemanticAstVisitor(
    clang::ASTContext &context,
    const ctk::analysis::v1::TraverseRequest &request,
    const IMatchBackend::Checkpoint &checkpoint, const TraversalLimits &limits,
    TraversalResult &result)
    : context_(context), request_(request), checkpoint_(checkpoint),
      limits_(limits), result_(result) {}
bool SemanticAstVisitor::shouldVisitImplicitCode() const {
  return request_.visit_implicit_code();
}
bool SemanticAstVisitor::shouldVisitTemplateInstantiations() const {
  return request_.visit_template_instantiations();
}
bool SemanticAstVisitor::enter(const clang::DynTypedNode &node) {
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
  if (static_cast<std::size_t>(result_.response.nodes_size()) >=
      std::min<std::size_t>(maximum, limits_.max_nodes)) {
    result_.code = MatchCode::ResourceExhausted;
    result_.message = "AST traversal node limit exceeded";
    return false;
  }
  ctk::analysis::v1::TraversalNode record;
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
  if (bytes > limits_.max_bytes - bytes_) {
    result_.code = MatchCode::ResourceExhausted;
    result_.message = "AST traversal response limit exceeded";
    return false;
  }
  bytes_ += bytes;
  parents_.push_back(result_.response.nodes_size());
  result_.response.add_nodes()->Swap(&record);
  return true;
}
bool SemanticAstVisitor::TraverseDecl(clang::Decl *declaration) {
  if (!declaration)
    return true;
  const auto &sources = context_.getSourceManager();
  if (request_.main_file_only() &&
      !llvm::isa<clang::TranslationUnitDecl>(declaration) &&
      declaration->getLocation().isValid() &&
      !sources.isWrittenInMainFile(
          sources.getExpansionLoc(declaration->getLocation())))
    return true;
  // Native RAV still visits explicit constraints on implicit template
  // parameters.
  if (declaration->isImplicit() && !shouldVisitImplicitCode())
    return clang::RecursiveASTVisitor<SemanticAstVisitor>::TraverseDecl(
        declaration);
  if (!enter(clang::DynTypedNode::create(*declaration)))
    return result_.code == MatchCode::Ok;
  const bool success =
      clang::RecursiveASTVisitor<SemanticAstVisitor>::TraverseDecl(declaration);
  parents_.pop_back();
  return success;
}
bool SemanticAstVisitor::dataTraverseStmtPre(clang::Stmt *statement) {
  const auto &sources = context_.getSourceManager();
  if (request_.main_file_only() && statement->getBeginLoc().isValid() &&
      !sources.isWrittenInMainFile(
          sources.getExpansionLoc(statement->getBeginLoc())))
    return false;
  return enter(clang::DynTypedNode::create(*statement));
}
bool SemanticAstVisitor::dataTraverseStmtPost(clang::Stmt *) {
  parents_.pop_back();
  return result_.code == MatchCode::Ok;
}
} // namespace ctk::clang_layer
