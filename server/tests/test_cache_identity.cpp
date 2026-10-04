#include "ctk/cache/compilation_context.hpp"
#include "ctk/cache/path_policy.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <stdexcept>
#include <string>

namespace {

ctk::cache::CompilationContext make_context() {
  ctk::cache::CompilationContext context;
  context.input_spelling = "src/main.cpp";
  context.working_directory = "/work/project";
  context.toolchain_identity = "clang-22/resource-a";
  context.arguments = {"clang++", "-std=c++23", "src/main.cpp"};
  context.environment = {{"Z", "last"}, {"A", "first"}};
  context.vfs_overlays = {"overlay-a.yaml", "overlay-b.yaml"};
  return context;
}

TEST(PathPolicy, KeepsExplicitSpellingAndDirectoryBoundaries) {
  EXPECT_EQ(ctk::cache::path_key("/srv/project/src/main.cpp/"),
            "/srv/project/src/main.cpp");
  EXPECT_EQ(ctk::cache::path_key("/"), "/");
  EXPECT_EQ(ctk::cache::directory_key("/srv/project/src/"), "/srv/project/src");
  EXPECT_EQ(ctk::cache::directory_prefix("/srv/project/src"),
            "/srv/project/src/");
  EXPECT_EQ(ctk::cache::directory_prefix("/"), "/");
  EXPECT_THROW(ctk::cache::path_key("/link/../target"), std::invalid_argument);
}

TEST(PathPolicy, RejectsUnsafeOrAmbiguousComponents) {
  for (const auto *path :
       {"", "relative/file", "/a//b", "/a/./b", "/a/../b", "/a///"}) {
    EXPECT_THROW(ctk::cache::path_key(path), std::invalid_argument) << path;
  }
  const std::string nul_path("/a\0b", 4);
  EXPECT_THROW(ctk::cache::path_key(nul_path), std::invalid_argument);
}

TEST(CompilationContext, CanonicalizesEnvironmentButPreservesOrderedInputs) {
  auto first = make_context();
  auto reordered_environment = first;
  std::reverse(reordered_environment.environment.begin(),
               reordered_environment.environment.end());
  EXPECT_EQ(first.canonical_bytes(), reordered_environment.canonical_bytes());
  EXPECT_NE(first.digest(), "");
  EXPECT_TRUE(first.canonical_bytes().starts_with("ctk-profile-v1:"));
  const auto bytes = first.canonical_bytes();
  std::size_t offset = 0;
  for (const auto *key :
       {"arguments", "environment", "input_spelling", "resource_directory",
        "reusable", "schema_version", "sysroot", "target", "toolchain_identity",
        "vfs_overlays", "working_directory"}) {
    const auto position = bytes.find(std::string("\"") + key + "\":", offset);
    ASSERT_NE(position, std::string::npos) << key;
    offset = position + 1;
  }

  auto changed_argument_order = first;
  std::reverse(changed_argument_order.arguments.begin(),
               changed_argument_order.arguments.end());
  EXPECT_NE(first.canonical_bytes(), changed_argument_order.canonical_bytes());
  auto changed_input = first;
  changed_input.input_spelling = "src/other.cpp";
  EXPECT_NE(first.canonical_bytes(), changed_input.canonical_bytes());
}

TEST(CompilationContext, SeparatesEveryIdentityField) {
  const auto original = make_context().canonical_bytes();
  auto check = [&](auto mutate) {
    auto context = make_context();
    mutate(context);
    EXPECT_NE(original, context.canonical_bytes());
  };
  check([](auto &c) { c.working_directory = "/work/other"; });
  check([](auto &c) { c.toolchain_identity = "clang-23/resource-a"; });
  check([](auto &c) { c.resource_directory = "/clang/resource"; });
  check([](auto &c) { c.target = "aarch64-unknown-linux-gnu"; });
  check([](auto &c) { c.sysroot = "/sysroot"; });
  check([](auto &c) { c.environment[0].second = "changed"; });
  check([](auto &c) { c.vfs_overlays[0] = "overlay-c.yaml"; });
  check([](auto &c) { c.reusable = false; });
}

TEST(CompilationContext, EscapesJsonControlsAndPreservesUnicodeBytes) {
  auto context = make_context();
  context.input_spelling = "src/café\n.cpp";
  const auto bytes = context.canonical_bytes();
  EXPECT_NE(bytes.find("café\\n.cpp"), std::string::npos);
  EXPECT_EQ(bytes.find("\n.cpp"), std::string::npos);
}

TEST(CompilationContext, RejectsInvalidIdentityAndDuplicateEnvironmentNames) {
  auto context = make_context();
  context.environment = {{"A", "one"}, {"A", "two"}};
  EXPECT_THROW(context.canonical_bytes(), std::invalid_argument);
  context.environment.clear();
  context.schema_version = 2;
  EXPECT_THROW(context.canonical_bytes(), std::invalid_argument);
  context.schema_version = 1;
  context.working_directory = "relative";
  EXPECT_THROW(context.canonical_bytes(), std::invalid_argument);
  context.working_directory = "/work/project";
  context.input_spelling.clear();
  EXPECT_THROW(context.canonical_bytes(), std::invalid_argument);
  context.input_spelling = std::string("bad\xc0\xaf", 5);
  EXPECT_THROW(context.canonical_bytes(), std::invalid_argument);
}

TEST(CompilationContext,
     DigestIsOnlyAnIndexAndCanonicalBytesStayAuthoritative) {
  const auto first = make_context().canonical_bytes();
  auto changed = make_context();
  changed.target = "different-target";
  const auto second = changed.canonical_bytes();

  EXPECT_NE(first, second);
  // A cache may inject a constant digest; equality must still use these bytes.
  const auto forced_digest = [](std::string_view) { return "collision"; };
  EXPECT_EQ(forced_digest(first), forced_digest(second));
}

} // namespace
