#include "ir.hpp"

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/ASTMatchers/Dynamic/Registry.h>
#include <llvm/AsmParser/Parser.h>
#include <llvm/ExecutionEngine/Orc/LLJIT.h>
#include <llvm/IR/Verifier.h>
#include <llvm/Support/SourceMgr.h>

namespace ctk::jit {
namespace {

namespace dynamic = clang::ast_matchers::dynamic;
using clang::FunctionDecl;
using clang::ast_matchers::MatchFinder;

// Layout of the generated LLVM IR's %arg on the runner's target.
struct MatcherArg {
  const char* name;
  const char* literal;
  const MatcherArg* children;
  std::uint32_t count;
};

struct IrContext {
  clang::ASTContext& ast;
  std::vector<const FunctionDecl*> rows;
  std::size_t next = 0;
  std::string error;
};

dynamic::VariantMatcher construct_matcher(const MatcherArg& arg,
                                          dynamic::Diagnostics& diagnostics) {
  auto ctor = dynamic::Registry::lookupMatcherCtor(arg.name);
  if (!ctor) {
    diagnostics.addError({}, dynamic::Diagnostics::ET_RegistryMatcherNotFound) << arg.name;
    return {};
  }
  std::vector<dynamic::ParserValue> args;
  args.reserve(arg.count);
  for (std::uint32_t index = 0; index < arg.count; ++index) {
    const auto& child = arg.children[index];
    auto& value = args.emplace_back().Value;
    if (child.literal) {
      value.setString(child.literal);
    } else {
      auto matcher = construct_matcher(child, diagnostics);
      if (matcher.isNull()) {
        return {};
      }
      value.setMatcher(matcher);
    }
  }
  return dynamic::Registry::constructMatcher(*ctor, {}, args, &diagnostics);
}

extern "C" int ctk_jit_match_v1(IrContext* context, const MatcherArg* root, const char* binding) {
  dynamic::Diagnostics diagnostics;
  auto matcher = construct_matcher(*root, diagnostics).getSingleMatcher();
  // Bind explicitly so an empty binding ID has the same behavior as .bind("").
  auto bound = matcher ? matcher->tryBind(binding) : std::nullopt;
  if (!bound) {
    context->error = diagnostics.errors().empty() ? "could not bind the IR query's matcher"
                                                  : diagnostics.toString();
    return 1;
  }

  struct CollectRows final : MatchFinder::MatchCallback {
    CollectRows(llvm::StringRef binding, std::vector<const FunctionDecl*>& rows)
        : binding(binding)
        , rows(rows) {}

    void run(const MatchFinder::MatchResult& result) override {
      if (const auto* decl = result.Nodes.getNodeAs<FunctionDecl>(binding)) {
        rows.push_back(decl);
      }
    }

    llvm::StringRef binding;
    std::vector<const FunctionDecl*>& rows;
  };

  CollectRows collect(binding, context->rows);
  MatchFinder finder;
  if (!finder.addDynamicMatcher(*bound, &collect)) {
    context->error = "could not register the IR query's matcher";
    return 1;
  }
  finder.matchAST(context->ast);
  return 0;
}

extern "C" const FunctionDecl* ctk_jit_next_row_v1(IrContext* context) {
  return context->next == context->rows.size() ? nullptr : context->rows[context->next++];
}

extern "C" void ctk_jit_print_decl_name_v1(const FunctionDecl* decl) {
  llvm::outs() << decl->getNameAsString() << '\n';
}

extern "C" void ctk_jit_print_qualified_name_v1(const FunctionDecl* decl) {
  llvm::outs() << decl->getQualifiedNameAsString() << '\n';
}

llvm::Error failure(const llvm::Twine& message) {
  return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
}

} // namespace

llvm::Error run_ir(llvm::StringRef source, clang::ASTContext& ast) {
  auto context = std::make_unique<llvm::LLVMContext>();
  llvm::SMDiagnostic diagnostic;
  auto module = llvm::parseAssemblyString(source, diagnostic, *context);
  if (!module) {
    diagnostic.print("ctk-jit", llvm::errs());
    return failure("could not parse generated LLVM IR");
  }
  auto jit = llvm::orc::LLJITBuilder().create();
  if (!jit) {
    return jit.takeError();
  }
  module->setDataLayout((*jit)->getDataLayout());
  module->setTargetTriple((*jit)->getTargetTriple());
  if (llvm::verifyModule(*module, &llvm::errs())) {
    return failure("generated LLVM IR failed verification");
  }

  llvm::orc::SymbolMap symbols;
  auto expose = [&](llvm::StringRef name, auto* function) {
    symbols[(*jit)->mangleAndIntern(name)] = {llvm::orc::ExecutorAddr::fromPtr(function),
                                              llvm::JITSymbolFlags::Exported |
                                                  llvm::JITSymbolFlags::Callable};
  };
  expose("ctk_jit_match_v1", &ctk_jit_match_v1);
  expose("ctk_jit_next_row_v1", &ctk_jit_next_row_v1);
  expose("ctk_jit_print_decl_name_v1", &ctk_jit_print_decl_name_v1);
  expose("ctk_jit_print_qualified_name_v1", &ctk_jit_print_qualified_name_v1);
  auto& dylib = (*jit)->getMainJITDylib();
  if (auto error = dylib.define(llvm::orc::absoluteSymbols(std::move(symbols)))) {
    return error;
  }
  if (auto error = (*jit)->addIRModule({std::move(module), std::move(context)})) {
    return error;
  }
  auto entry = (*jit)->lookup("ctk_jit_run_ir_v1");
  if (!entry) {
    return entry.takeError();
  }

  IrContext runtime{ast, {}, 0, {}};
  if (entry->toPtr<int (*)(IrContext*)>()(&runtime) != 0) {
    return failure(llvm::Twine("LLVM IR query: ") + runtime.error);
  }
  return llvm::Error::success();
}

} // namespace ctk::jit
