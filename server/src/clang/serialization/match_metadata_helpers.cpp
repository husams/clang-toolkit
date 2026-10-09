#include "match_metadata_helpers.hpp"

#include <clang/AST/ExprCXX.h>
#include <clang/AST/ParentMapContext.h>
#include <clang/AST/RawCommentList.h>
#include <clang/Basic/SourceManager.h>
#include <clang/Index/USRGeneration.h>
#include <llvm/ADT/SmallString.h>
#include <algorithm>
#include <string>
#include <vector>

namespace ctk::clang_layer::serialization::helpers {
namespace {
using ctk::match::v1::MatchSourcePoint;

void write_point(clang::SourceLocation source, clang::SourceLocation coordinate,
                 clang::SourceManager &manager, MatchSourcePoint *out) {
  out->set_is_macro(source.isMacroID());
  if (coordinate.isInvalid())
    return;
  bool invalid_line = false;
  bool invalid_column = false;
  const auto filename = manager.getFilename(coordinate);
  const auto [file, offset] = manager.getDecomposedLoc(coordinate);
  const auto line = manager.getLineNumber(file, offset, &invalid_line);
  const auto column = manager.getColumnNumber(file, offset, &invalid_column);
  if (filename.empty() || invalid_line || invalid_column || line == 0 ||
      column == 0)
    return;
  out->set_file(filename.str());
  out->set_line(line);
  out->set_column(column);
  out->set_valid(true);
}

void write_source_range(clang::SourceRange range,
                        clang::SourceManager &manager,
                        ctk::match::v1::MatchBinding &binding) {
  if (range.isInvalid())
    return;
  auto *out = binding.mutable_range();
  const auto begin = range.getBegin();
  const auto end = range.getEnd();
  write_point(begin, manager.getExpansionLoc(begin), manager,
              out->mutable_expansion_begin());
  write_point(end, manager.getExpansionLoc(end), manager,
              out->mutable_expansion_end());
  write_point(begin, manager.getSpellingLoc(begin), manager,
              out->mutable_spelling_begin());
  write_point(end, manager.getSpellingLoc(end), manager,
              out->mutable_spelling_end());
}

std::string symbol_identity(const clang::NamedDecl &declaration) {
  llvm::SmallString<128> usr;
  if (clang::index::generateUSRForDecl(&declaration, usr))
    return {};
  return usr.str().str();
}

const clang::FunctionDecl *enclosing_function(const clang::CallExpr &call,
                                              clang::ASTContext &context) {
  std::vector<clang::DynTypedNode> frontier{clang::DynTypedNode::create(call)};
  std::vector<clang::DynTypedNode> seen = frontier;
  while (!frontier.empty()) {
    std::vector<clang::DynTypedNode> next;
    const clang::FunctionDecl *nearest = nullptr;
    for (const auto &current : frontier) {
      for (const auto &parent : context.getParents(current)) {
        if (const auto *function = parent.get<clang::FunctionDecl>()) {
          if (!nearest)
            nearest = function;
          continue;
        }
        if (std::find(seen.begin(), seen.end(), parent) == seen.end() &&
            std::find(next.begin(), next.end(), parent) == next.end()) {
          seen.push_back(parent);
          next.push_back(parent);
        }
      }
    }
    if (nearest)
      return nearest;
    frontier = std::move(next);
  }
  return nullptr;
}

bool explicitly_qualified_call(const clang::CallExpr &call) {
  const auto *member = llvm::dyn_cast<clang::MemberExpr>(
      call.getCallee()->IgnoreParenImpCasts());
  return member && member->hasQualifier();
}

void write_call_site(const clang::CallExpr &call,
                     ctk::match::v1::MatchBinding &binding,
                     SerializationContext &context) {
  auto *facts = binding.mutable_call_site();
  if (const auto *caller = enclosing_function(call, context.ast_context)) {
    facts->set_caller_name(caller->getQualifiedNameAsString());
    facts->set_caller_symbol_identity(symbol_identity(*caller));
  }
  const auto *callee = call.getDirectCallee();
  if (!callee) {
    facts->set_dispatch(ctk::match::v1::CALL_DISPATCH_INDIRECT);
    return;
  }
  facts->set_static_callee_name(callee->getQualifiedNameAsString());
  facts->set_static_callee_symbol_identity(symbol_identity(*callee));
  const auto *method = llvm::dyn_cast<clang::CXXMethodDecl>(callee);
  const bool virtual_dispatch = method && method->isVirtual() &&
                                !explicitly_qualified_call(call);
  facts->set_dispatch(virtual_dispatch
                          ? ctk::match::v1::CALL_DISPATCH_VIRTUAL
                          : ctk::match::v1::CALL_DISPATCH_DIRECT);
}
} // namespace

void write_match_metadata(const clang::DynTypedNode &node,
                          ctk::match::v1::MatchBinding &binding,
                          SerializationContext &context) {
  clang::SourceRange range;
  if (const auto *declaration = node.get<clang::Decl>()) {
    range = declaration->getSourceRange();
    if (const auto *named = llvm::dyn_cast<clang::NamedDecl>(declaration)) {
      binding.set_symbol_identity(symbol_identity(*named));
      if (const auto *comment =
              context.ast_context.getRawCommentForDeclNoCache(named)) {
        const auto text = comment->getRawText(
            context.ast_context.getSourceManager());
        binding.set_documentation(text.str());
      }
    }
  } else if (const auto *statement = node.get<clang::Stmt>()) {
    range = statement->getSourceRange();
    if (const auto *call = llvm::dyn_cast<clang::CallExpr>(statement))
      write_call_site(*call, binding, context);
  } else {
    range = node.getSourceRange();
  }

  if (range.isInvalid())
    return;
  auto &manager = context.ast_context.getSourceManager();
  write_point(range.getBegin(), manager.getExpansionLoc(range.getBegin()),
              manager, binding.mutable_location());
  write_source_range(range, manager, binding);
}

} // namespace ctk::clang_layer::serialization::helpers
