#include "ctk/clang/project_index_extract.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <gtest/gtest.h>
#include <tuple>

namespace ctk::clang_layer {
namespace {
class DefinitionIndex : public ::testing::Test {
protected:
  platform::TemporaryDirectory directory{"ctk-definition-index"};
  platform::TemporaryDirectory cache_directory{"ctk-definition-cache"};
  std::filesystem::path root = directory.path();
  void write(const char *name, const std::string &text) {
    std::ofstream(root / name) << text;
  }
  ProjectIndexExtraction extract(const char *name,
                                 std::vector<std::string> args = {},
                                 bool cache = true) {
    ProjectIndexExtraction result;
    std::string error;
    args.insert(args.begin(), {"-std=c++20", "-I" + root.string()});
    EXPECT_TRUE(extract_project_index(
        (root / name).string(), root.string(), root.string(), args, result,
        error, cache ? cache_directory.path().string() : ""))
        << error;
    return result;
  }
  auto rows(const ProjectIndexExtraction &result) {
    std::vector<
        std::tuple<std::string, std::string, std::string, std::string,
                   std::string, unsigned, unsigned, std::uint64_t, bool>>
        values;
    for (const auto &s : result.symbols)
      values.emplace_back(s.usr, s.qualified_name, s.kind, s.file_path,
                          s.signature, s.line, s.column, s.byte_offset,
                          s.is_definition);
    std::sort(values.begin(), values.end());
    return values;
  }
  bool has(const ProjectIndexExtraction &r, const std::string &name) {
    return std::any_of(r.symbols.begin(), r.symbols.end(),
                       [&](const auto &s) { return s.qualified_name == name; });
  }
  bool has_spelling_name(const ProjectIndexExtraction &r,
                         const std::string &name) {
    return std::any_of(r.symbols.begin(), r.symbols.end(),
                       [&](const auto &s) { return s.name == name; });
  }
  void common() {
    write("shared.hpp",
          "#pragma once\n#ifndef FLAVOR\n#define FLAVOR 1\n#endif\n#if FLAVOR "
          "== 1\nstruct Alpha { int field; };\n#else\nstruct Beta { long "
          "field; };\n#endif\nstatic int file_private = 1;\nnamespace "
          "{ struct HeaderPrivate {}; }\ninline int shared(){ return "
          "FLAVOR; }\n");
    write("one.cpp", "#include \"shared.hpp\"\nint one(){return shared();}\n");
    write("two.cpp", "#include \"shared.hpp\"\nint two(){return shared();}\n");
  }
};
TEST_F(DefinitionIndex,
       KeepsDefinitionsAndDefiningAliasesWhileDroppingDeclarationOnlyEntities) {
  write("one.cpp", R"cpp(
#include <vector>
struct Forward;
extern int declared;
int prototype(int parameter);
struct Complete { static int member; int field; Complete() = default; void removed() = delete; };
int Complete::member = 1;
int defined = 2;
inline int body(){ return defined; }
template<class T> T function(T value){return value;}
template<class T> struct Template { T field; };
template<class T> using AliasTemplate = Template<T>;
using Alias = Complete;
typedef int Integer;
enum Color { Red };
template<class T> concept Small = sizeof(T) < 8;
)cpp");
  const auto result = extract("one.cpp");
  EXPECT_FALSE(has(result, "Forward"));
  EXPECT_FALSE(has(result, "declared"));
  EXPECT_FALSE(has(result, "prototype"));
  for (const auto &name :
       {"Complete", "Complete::member", "Complete::field", "Complete::Complete",
        "Complete::removed", "defined", "body", "function", "Template",
        "AliasTemplate", "Alias", "Integer", "Color", "Red", "Small"})
    EXPECT_TRUE(has(result, name)) << name;
  EXPECT_FALSE(result.symbols.empty());
  for (const auto &symbol : result.symbols) {
    EXPECT_TRUE(symbol.is_definition);
    EXPECT_TRUE(symbol.signature.empty());
    EXPECT_FALSE(symbol.qualified_name.starts_with("std::"));
  }
}
TEST_F(DefinitionIndex, KeepsExternalDefinitionsAndOmitsFunctionLocals) {
  write("one.cpp", R"cpp(
struct Pair { int first; int second; };
struct PublicType { int field; enum Kind { Value }; };
using PublicAlias = PublicType;
constexpr int constant_function() { int local_binding = 4; return local_binding; }
auto deduced_function() {
  struct LocalType { int member; };
  auto local_lambda = [] { return 1; };
  auto [local_left, local_right] = Pair{2, 3};
  return local_left + local_lambda() + sizeof(LocalType) + local_right;
}
auto deduced_global = deduced_function();
)cpp");
  const auto result = extract("one.cpp");
  for (const auto &name :
       {"Pair", "Pair::first", "Pair::second", "PublicType",
        "PublicType::field", "PublicType::Kind", "PublicType::Value",
        "PublicAlias", "constant_function", "deduced_function",
        "deduced_global"})
    EXPECT_TRUE(has(result, name)) << name;
  for (const auto &name : {"local_binding", "LocalType", "member",
                           "local_lambda", "local_left", "local_right"})
    EXPECT_FALSE(has_spelling_name(result, name)) << name;
  for (const auto &symbol : result.symbols)
    EXPECT_TRUE(symbol.signature.empty()) << symbol.qualified_name;
}
TEST_F(DefinitionIndex, SkippedFunctionBodiesDoNotRequireBodyDiagnostics) {
  write("one.cpp", "int indexed_function() { return undeclared_in_body; }\n");
  const auto result = extract("one.cpp");
  EXPECT_TRUE(has(result, "indexed_function"));
}
TEST_F(DefinitionIndex,
       ReusesExactHeaderDefinitionsAcrossTusWithoutChangingResults) {
  common();
  EXPECT_EQ(extract("one.cpp").reused_header_symbols, 0);
  const auto cached = extract("two.cpp");
  EXPECT_GT(cached.reused_header_symbols, 0);
  EXPECT_EQ(rows(cached), rows(extract("two.cpp", {}, false)));
  EXPECT_TRUE(has(cached, "two"));
  EXPECT_FALSE(has(cached, "one"));
}
TEST_F(DefinitionIndex,
       OmitsInternalDefinitionsButKeepsExternalTemplateAndFriend) {
  write("shared.hpp", R"cpp(
#pragma once
static int internal_value = 1;
namespace { struct Hidden { int field; }; inline int hidden(){struct Local {int value;}; return sizeof(Local);} }
template<class T> T echo(T value){return value;}
struct Friend { friend int visit(Friend){return internal_value;} };
)cpp");
  write("one.cpp", "#include \"shared.hpp\"\n");
  write("two.cpp", "#include \"shared.hpp\"\n");
  extract("one.cpp");
  const auto result = extract("two.cpp");
  EXPECT_GT(result.reused_header_symbols, 0);
  EXPECT_EQ(rows(result), rows(extract("two.cpp", {}, false)));
  EXPECT_FALSE(has_spelling_name(result, "internal_value"));
  EXPECT_FALSE(has_spelling_name(result, "Hidden"));
  EXPECT_FALSE(has_spelling_name(result, "hidden"));
  EXPECT_TRUE(has(result, "echo"));
  EXPECT_TRUE(has(result, "Friend"));
  EXPECT_TRUE(has(result, "visit"));
}
TEST_F(DefinitionIndex, ReusesNestedHeaderAcrossDifferentWrappers) {
  write("shared.hpp", "#pragma once\nstruct Shared { int field; };\n");
  write("a.hpp", "#include \"shared.hpp\"\nstruct OuterA {};\n");
  write("b.hpp", "#include \"shared.hpp\"\nstruct OuterB {};\n");
  write("one.cpp", "#include \"a.hpp\"\nint one(){return 1;}\n");
  write("two.cpp", "#include \"b.hpp\"\nint two(){return 2;}\n");
  extract("one.cpp");
  const auto cached = extract("two.cpp");
  EXPECT_GT(cached.reused_header_symbols, 0);
  EXPECT_EQ(rows(cached), rows(extract("two.cpp", {}, false)));
  EXPECT_TRUE(has(cached, "OuterB"));
  EXPECT_FALSE(has(cached, "OuterA"));
}
TEST_F(DefinitionIndex, ExtractsDeclarationsCompletedOutsideHeaderLive) {
  write("shared.hpp", "inline int split(\n");
  write("one.cpp", "#include \"shared.hpp\"\nint x){return x;}\n");
  write("two.cpp", "#include \"shared.hpp\"\nlong x){return x;}\n");
  extract("one.cpp");
  EXPECT_EQ(rows(extract("two.cpp")), rows(extract("two.cpp", {}, false)));
  write("shared.hpp",
        "inline int good(){return 1;}\nnamespace split {\ninline int inner(\n");
  write("one.cpp", "#include \"shared.hpp\"\nint x){return x;} }\n");
  write("two.cpp", "#include \"shared.hpp\"\nlong x){return x;} }\n");
  extract("one.cpp");
  const auto mixed = extract("two.cpp");
  EXPECT_GT(mixed.reused_header_symbols, 0);
  EXPECT_EQ(rows(mixed), rows(extract("two.cpp", {}, false)));
}
TEST_F(DefinitionIndex, ReusesHeadersAfterLiteralMacroStackPragmas) {
  write("shared.hpp",
        "#pragma once\n#define PUSH "
        "_Pragma(\"push_macro(\\\"FLAVOR\\\")\")\nPUSH\ninline int "
        "shared(){return 1;}\n_Pragma(\"pop_macro(\\\"FLAVOR\\\")\")\n");
  write("one.cpp", "#include \"shared.hpp\"\n");
  write("two.cpp", "#include \"shared.hpp\"\n");
  extract("one.cpp");
  const auto cached = extract("two.cpp");
  EXPECT_GT(cached.reused_header_symbols, 0);
  EXPECT_EQ(rows(cached), rows(extract("two.cpp", {}, false)));
}
TEST_F(DefinitionIndex, ReusesHeadersWithExplicitSemanticPragmas) {
  write("shared.hpp",
        "#pragma once\n#pragma GCC visibility push(default)\n#pragma clang "
        "assume_nonnull begin\ninline int *shared(){return nullptr;}\n#pragma "
        "clang assume_nonnull end\n#pragma GCC visibility pop\n");
  write("one.cpp", "#include \"shared.hpp\"\n");
  write("two.cpp", "#include \"shared.hpp\"\n");
  extract("one.cpp");
  const auto result = extract("two.cpp");
  EXPECT_GT(result.reused_header_symbols, 0);
  EXPECT_EQ(rows(result), rows(extract("two.cpp", {}, false)));
}
TEST_F(DefinitionIndex, UnknownPragmasUseLiveExtraction) {
  write("shared.hpp", "#pragma pack(push,1)\nstruct Packed{char a;long "
                      "b;};\n#pragma pack(pop)\n");
  write("one.cpp", "#include \"shared.hpp\"\n");
  write("two.cpp", "#include \"shared.hpp\"\n");
  extract("one.cpp");
  const auto result = extract("two.cpp");
  EXPECT_EQ(result.reused_header_symbols, 0);
  EXPECT_EQ(rows(result), rows(extract("two.cpp", {}, false)));
}
TEST_F(DefinitionIndex, PreservesCommandAndSourceMacroContextsAndHeaderEdits) {
  common();
  extract("one.cpp");
  auto beta = extract("two.cpp", {"-DFLAVOR=2"});
  EXPECT_EQ(beta.reused_header_symbols, 0);
  EXPECT_TRUE(has(beta, "Beta"));
  EXPECT_FALSE(has(beta, "Alpha"));
  EXPECT_GT(extract("one.cpp", {"-DFLAVOR=2"}).reused_header_symbols, 0);
  const auto warm_beta = extract("one.cpp", {"-DFLAVOR=2"});
  EXPECT_EQ(rows(warm_beta), rows(extract("one.cpp", {"-DFLAVOR=2"}, false)));
  EXPECT_TRUE(has(warm_beta, "Beta"));
  EXPECT_FALSE(has(warm_beta, "Alpha"));
  EXPECT_FALSE(has_spelling_name(warm_beta, "file_private"));
  EXPECT_FALSE(has_spelling_name(warm_beta, "HeaderPrivate"));
  write("two.cpp", "#define FLAVOR 2\n#include \"shared.hpp\"\nint "
                   "two(){return shared();}\n");
  EXPECT_EQ(rows(extract("two.cpp")), rows(extract("two.cpp", {}, false)));
  write("shared.hpp",
        "#pragma once\nstruct Changed {};\ninline int shared(){return 7;}\n");
  auto changed = extract("one.cpp");
  EXPECT_EQ(changed.reused_header_symbols, 0);
  EXPECT_TRUE(has(changed, "Changed"));
  EXPECT_FALSE(has(changed, "Alpha"));
}
TEST_F(DefinitionIndex,
       SkippedFunctionBodiesPreserveMacroAndCounterEffectsForHeaders) {
  write("shared.hpp", R"cpp(
#pragma once
#if FLAVOR == 2
struct Beta {};
#else
struct Alpha {};
#endif
#if __COUNTER__ == 1
struct ExpectedCounter {};
#else
struct UnexpectedCounter {};
#endif
)cpp");
  const std::string source = R"cpp(
int body() {
#define FLAVOR 2
  int local = __COUNTER__;
  return local;
}
#include "shared.hpp"
)cpp";
  write("one.cpp", source);
  write("two.cpp", source);
  const auto first = extract("one.cpp");
  EXPECT_TRUE(has(first, "Beta"));
  EXPECT_TRUE(has(first, "ExpectedCounter"));
  EXPECT_FALSE(has(first, "Alpha"));
  EXPECT_FALSE(has(first, "UnexpectedCounter"));
  EXPECT_FALSE(has_spelling_name(first, "local"));

  const auto warm = extract("two.cpp");
  EXPECT_EQ(rows(warm), rows(extract("two.cpp", {}, false)));
  EXPECT_TRUE(has(warm, "Beta"));
  EXPECT_TRUE(has(warm, "ExpectedCounter"));
  EXPECT_FALSE(has(warm, "Alpha"));
  EXPECT_FALSE(has(warm, "UnexpectedCounter"));
  EXPECT_FALSE(has_spelling_name(warm, "local"));
}
TEST_F(DefinitionIndex, FallsBackForPriorDeclarationsAndVolatileMacroContexts) {
  common();
  extract("one.cpp");
  write("two.cpp", "namespace ns {\n#include \"shared.hpp\"\n}\nint "
                   "two(){return ns::shared();}\n");
  auto nested = extract("two.cpp");
  EXPECT_EQ(nested.reused_header_symbols, 0);
  EXPECT_EQ(rows(nested), rows(extract("two.cpp", {}, false)));
  write("shared.hpp", "#pragma once\ninline int shared(){return 1;}\ninline "
                      "const char *origin(){ return __BASE_FILE__; }\n");
  write("two.cpp", "#include \"shared.hpp\"\n");
  extract("one.cpp");
  auto volatile_result = extract("two.cpp");
  EXPECT_EQ(volatile_result.reused_header_symbols, 0);
  EXPECT_EQ(rows(volatile_result), rows(extract("two.cpp", {}, false)));
}
TEST_F(DefinitionIndex,
       IncludesSelectionAndMainFileMacroDefinitionsRemainFresh) {
  common();
  write("shared.hpp",
        "#pragma once\n#if __has_include(\"optional.hpp\")\nstruct Present "
        "{};\n#else\nstruct Absent {};\n#endif\n#define DEFINE(NAME) int "
        "NAME(){return 1;}\n");
  write("one.cpp", "#include \"shared.hpp\"\nDEFINE(first)\n");
  write("two.cpp", "#include \"shared.hpp\"\nDEFINE(second)\n");
  extract("one.cpp");
  auto second = extract("two.cpp");
  EXPECT_TRUE(has(second, "second"));
  EXPECT_FALSE(has(second, "first"));
  EXPECT_EQ(rows(second), rows(extract("two.cpp", {}, false)));
  write("optional.hpp", "");
  auto present = extract("two.cpp");
  EXPECT_TRUE(has(present, "Present"));
  EXPECT_FALSE(has(present, "Absent"));
  EXPECT_EQ(rows(present), rows(extract("two.cpp", {}, false)));
}
TEST_F(DefinitionIndex,
       RejectsSameSizeEditsAndSymlinkRetargetsWithIdenticalContents) {
  common();
  const std::string before = "#pragma once\nstruct Alpha {};\n";
  const std::string after = "#pragma once\nstruct Omega {};\n";
  write("shared.hpp", before);
  write("one.cpp", "#include \"shared.hpp\"\n");
  write("two.cpp", "#include \"shared.hpp\"\n");
  const auto stamp = std::filesystem::last_write_time(root / "shared.hpp");
  extract("one.cpp");
  write("shared.hpp", after);
  std::filesystem::last_write_time(root / "shared.hpp", stamp);
  auto changed = extract("two.cpp");
  EXPECT_EQ(changed.reused_header_symbols, 0);
  EXPECT_TRUE(has(changed, "Omega"));
  EXPECT_FALSE(has(changed, "Alpha"));
  write("original.hpp", after);
  write("replacement.hpp", after);
  std::filesystem::remove(root / "shared.hpp");
  std::filesystem::create_symlink(root / "original.hpp", root / "shared.hpp");
  extract("one.cpp");
  std::filesystem::remove(root / "shared.hpp");
  std::filesystem::create_symlink(root / "replacement.hpp",
                                  root / "shared.hpp");
  const auto retargeted = extract("two.cpp");
  EXPECT_EQ(retargeted.reused_header_symbols, 0);
  EXPECT_EQ(rows(retargeted), rows(extract("two.cpp", {}, false)));
}
TEST_F(DefinitionIndex, ForcedIncludesAlwaysUseLiveExtraction) {
  common();
  write("forced.hpp", "#define FLAVOR 2\n");
  const std::vector<std::string> args{"-include",
                                      (root / "forced.hpp").string()};
  extract("one.cpp", args);
  auto result = extract("two.cpp", args);
  EXPECT_EQ(result.reused_header_symbols, 0);
  EXPECT_TRUE(has(result, "Beta"));
  EXPECT_FALSE(has(result, "Alpha"));
  EXPECT_EQ(rows(result), rows(extract("two.cpp", args, false)));
}
TEST_F(DefinitionIndex, IgnoresCorruptCacheEntries) {
  common();
  extract("one.cpp");
  for (const auto &entry :
       std::filesystem::directory_iterator(cache_directory.path()))
    std::ofstream(entry.path(), std::ios::trunc) << "corrupt";
  const auto result = extract("two.cpp");
  EXPECT_EQ(result.reused_header_symbols, 0);
  EXPECT_EQ(rows(result), rows(extract("two.cpp", {}, false)));
}
} // namespace
} // namespace ctk::clang_layer
