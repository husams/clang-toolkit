#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include <fstream>
#include <gtest/gtest.h>
#include <string>
#include <vector>

namespace ctk::clang_layer {
namespace {

std::vector<ctk::match::v1::MatchBinding>
match_base(const std::string &source, const std::string &record_name) {
  ctk::platform::TemporaryDirectory directory{"ctk-base-specifier-semantics"};
  const auto path = directory.path() / "fixture.cc";
  std::ofstream(path) << source;
  FileInput file{path.string(), {"-std=c++20"}, directory.path().string()};

  std::vector<ctk::match::v1::MatchBinding> result;
  const auto matcher = "cxxRecordDecl(hasName(\"" + record_name +
                       "\"), hasAnyBase(cxxBaseSpecifier().bind(\"base\")))";
  auto engine = make_query_engine();
  const auto status = engine->match(
      file, matcher, [] { return true; },
      [&](const IQueryEngine::Bindings &row) {
        result.push_back(row.at("base").value);
      });
  EXPECT_TRUE(status.ok) << status.message;
  return result;
}

TEST(BaseSpecifierSemantics,
     ExplicitAccessAndVirtualnessProduceCompleteTypedShallowValue) {
  const auto rows = match_base(
      "struct Base {}; struct Derived : public virtual Base {};", "Derived");
  ASSERT_EQ(rows.size(), 1U);

  const auto &binding = rows.front();
  ASSERT_EQ(binding.value_case(), ctk::match::v1::MatchBinding::kBaseSpecifier);
  const auto &base = binding.base_specifier();
  ASSERT_TRUE(base.has_access());
  EXPECT_EQ(base.access(), ctk::ast::v1::ACCESS_SPECIFIER_PUBLIC);
  ASSERT_TRUE(base.has_is_virtual());
  EXPECT_TRUE(base.is_virtual());
  ASSERT_TRUE(base.has_is_pack_expansion());
  EXPECT_FALSE(base.is_pack_expansion());
  ASSERT_TRUE(base.has_type());
  EXPECT_EQ(base.type().description().spelling(), "Base");
  EXPECT_TRUE(binding.is_complete());
  EXPECT_EQ(binding.supported_scopes_size(), 0);
  EXPECT_FALSE(binding.has_unsupported());

  bool type_unrequested = false;
  for (const auto &availability : binding.availability())
    if (availability.state() == ctk::ast::v1::FIELD_STATE_UNREQUESTED &&
        availability.field_path().ends_with("QualType.type"))
      type_unrequested = true;
  EXPECT_TRUE(type_unrequested);
}

TEST(BaseSpecifierSemantics, DefaultAccessUsesEffectiveClassOrStructAccess) {
  auto rows = match_base("struct Base {}; class Derived : Base {};", "Derived");
  ASSERT_EQ(rows.size(), 1U);
  ASSERT_TRUE(rows.front().has_base_specifier());
  EXPECT_EQ(rows.front().base_specifier().access(),
            ctk::ast::v1::ACCESS_SPECIFIER_PRIVATE);
  EXPECT_TRUE(rows.front().is_complete());
  EXPECT_FALSE(rows.front().has_unsupported());

  rows = match_base("struct Base {}; struct Derived : Base {};", "Derived");
  ASSERT_EQ(rows.size(), 1U);
  ASSERT_TRUE(rows.front().has_base_specifier());
  EXPECT_EQ(rows.front().base_specifier().access(),
            ctk::ast::v1::ACCESS_SPECIFIER_PUBLIC);
  EXPECT_FALSE(rows.front().has_unsupported());
}

TEST(BaseSpecifierSemantics, PackExpansionFlagIsSerialized) {
  const auto rows = match_base(
      "template <class... Bases> struct Derived : Bases... {};", "Derived");
  ASSERT_EQ(rows.size(), 1U);
  ASSERT_TRUE(rows.front().has_base_specifier());
  ASSERT_TRUE(rows.front().base_specifier().has_is_pack_expansion());
  EXPECT_TRUE(rows.front().base_specifier().is_pack_expansion());
  EXPECT_TRUE(rows.front().is_complete());
  EXPECT_FALSE(rows.front().has_unsupported());
}

} // namespace
} // namespace ctk::clang_layer
