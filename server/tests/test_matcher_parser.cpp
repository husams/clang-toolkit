#include "../src/clang/matcher_parser.hpp"
#include <clang/ASTMatchers/Dynamic/Parser.h>
#include <gtest/gtest.h>

namespace ctk::clang_layer {
namespace {
namespace dynamic = clang::ast_matchers::dynamic;

TEST(MatcherParser, CanonicalTypeDeclarationMismatchReportsTypesAndLocation) {
  llvm::StringRef query = R"query(varDecl(
    hasType(
           hasCanonicalType(
               cxxRecordDecl(hasName("X")).bind("type")
           )
    )
).bind("var"))query";
  dynamic::Diagnostics diagnostics;
  EXPECT_FALSE(parse_matcher_expression(query, diagnostics));
  const auto message = diagnostics.toStringFull();
  EXPECT_NE(message.find("3:12: Error building matcher hasCanonicalType."),
            std::string::npos) << message;
  EXPECT_NE(message.find("4:16: Incorrect type for arg 1."), std::string::npos)
      << message;
  EXPECT_NE(message.find("Expected = Matcher<QualType>"), std::string::npos)
      << message;
  EXPECT_NE(message.find("Actual = Matcher<Decl>"), std::string::npos) << message;
}

TEST(MatcherParser, ExistingClangDiagnosticsArePreserved) {
  for (const char *expression : {"invalidMatcher()", "varDecl(hasName(123))",
                                 "varDecl(hasName(\"x\")"}) {
    SCOPED_TRACE(expression);
    llvm::StringRef original_text(expression);
    dynamic::Diagnostics original;
    ASSERT_FALSE(dynamic::Parser::parseMatcherExpression(original_text, &original));
    ASSERT_FALSE(original.errors().empty());
    llvm::StringRef text(expression);
    dynamic::Diagnostics diagnostics;
    EXPECT_FALSE(parse_matcher_expression(text, diagnostics));
    EXPECT_EQ(diagnostics.toStringFull(), original.toStringFull());
  }
}

} // namespace
} // namespace ctk::clang_layer
