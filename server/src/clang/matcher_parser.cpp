#include "matcher_parser.hpp"
#include <clang/ASTMatchers/Dynamic/Parser.h>
#include <string>

namespace ctk::clang_layer {
namespace {
namespace dynamic = clang::ast_matchers::dynamic;

class DiagnosticSema final : public dynamic::Parser::RegistrySema {
public:
  dynamic::VariantMatcher actOnMatcherExpression(
      dynamic::MatcherCtor ctor, dynamic::SourceRange range,
      llvm::StringRef bind_id, llvm::ArrayRef<dynamic::ParserValue> args,
      dynamic::Diagnostics *diagnostics) override {
    auto matcher = RegistrySema::actOnMatcherExpression(
        ctor, range, bind_id, args, diagnostics);
    if (!matcher.isNull() || !diagnostics->errors().empty())
      return matcher;

    // Some Clang constructors reject incompatible arguments without recording
    // an error. Only after that rejection, consult the registry's accepted
    // argument types to explain the failure; never change valid expressions.
    for (unsigned index = 0; index < args.size(); ++index) {
      const std::pair<dynamic::MatcherCtor, unsigned> context{ctor, index};
      const auto accepted = getAcceptedCompletionTypes({context});
      unsigned specificity = 0;
      if (accepted.empty() ||
          args[index].Value.isConvertibleTo(accepted, &specificity))
        continue;
      std::string expected;
      for (const auto &kind : accepted) {
        if (!expected.empty())
          expected += "|";
        expected += kind.asString();
      }
      diagnostics->addError(args[index].Range,
                            dynamic::Diagnostics::ET_RegistryWrongArgType)
          << index + 1 << expected << args[index].Value.getTypeAsString();
    }
    if (diagnostics->errors().empty())
      diagnostics->addError(range,
                            dynamic::Diagnostics::ET_ParserFailedToBuildMatcher)
          << "Clang rejected the matcher without diagnostic details";
    return matcher;
  }
};
} // namespace

std::optional<clang::ast_matchers::internal::DynTypedMatcher>
parse_matcher_expression(llvm::StringRef &text,
                         dynamic::Diagnostics &diagnostics) {
  DiagnosticSema sema;
  auto matcher = dynamic::Parser::parseMatcherExpression(text, &sema, &diagnostics);
  if (!matcher && diagnostics.errors().empty())
    diagnostics.addError({}, dynamic::Diagnostics::ET_ParserFailedToBuildMatcher)
        << "Clang rejected the expression without diagnostic details";
  return matcher;
}

} // namespace ctk::clang_layer
