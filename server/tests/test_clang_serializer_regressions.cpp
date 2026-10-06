#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include "ast/v1/node.pb.h"
#include "ast/v1/record_type.pb.h"

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <string>

namespace ctk::clang_layer {
namespace {

TEST(ClangSerializerRegressions,
     PreservesAliasObjectTypeAndSerializesDirectRecordType) {
  ctk::platform::TemporaryDirectory directory("ctk-object-type-regression");
  const auto path = directory.path() / "fixture.cc";
  {
    std::ofstream output(path);
    output << "struct Box { int get() { return 7; } };\n"
              "using Alias = Box;\n"
              "int through_alias(Alias& box) { return box.get(); }\n"
              "int direct(Box& box) { return box.get(); }\n";
  }

  auto engine = make_query_engine();
  const FileInput file{
      path.string(), {"-std=c++20"}, std::filesystem::current_path().string()};
  const auto check_function_type = [&](const std::string &function_name,
                                       bool alias_object) {
    std::size_t matches = 0;
    bool saw_expected_type = false;
    const auto query = "callExpr(hasAncestor(functionDecl(hasName(\"" +
                       function_name + "\")))).bind(\"call\")";
    const auto result = engine->match(
        file, query, [] { return true; },
        [&](const IQueryEngine::Bindings &bindings) {
          ++matches;
          const auto &call = bindings.at("call").value.node();
          ASSERT_TRUE(call.has_cxx_member_call_expr());
          const auto &object_type =
              call.cxx_member_call_expr().object_type().type().node();
          ASSERT_FALSE(object_type.type_url().empty());

          if (alias_object &&
              object_type.type_url().ends_with("/ctk.ast.v1.TypedefType")) {
            saw_expected_type = true;
            return;
          }
          if (!alias_object &&
              object_type.type_url().ends_with("/ctk.ast.v1.RecordType")) {
            ctk::ast::v1::RecordType record;
            ASSERT_TRUE(object_type.UnpackTo(&record));
            EXPECT_EQ(record.info().spelling(), "Box");
            saw_expected_type = true;
            return;
          }

          ASSERT_TRUE(
              object_type.type_url().ends_with("/ctk.ast.v1.UnsupportedValue"));
          ctk::ast::v1::UnsupportedValue unsupported;
          ASSERT_TRUE(object_type.UnpackTo(&unsupported));
          EXPECT_EQ(unsupported.clang_class(), "ElaboratedType");
          EXPECT_EQ(unsupported.reason(),
                    ctk::ast::v1::UNSUPPORTED_REASON_DEFERRED_CONTRACT);
          saw_expected_type = true;
        });

    EXPECT_TRUE(result.ok) << result.message;
    EXPECT_EQ(matches, 1U);
    EXPECT_TRUE(saw_expected_type);
  };

  check_function_type("through_alias", true);
  check_function_type("direct", false);
}

} // namespace
} // namespace ctk::clang_layer
