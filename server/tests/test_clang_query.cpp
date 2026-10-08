#include "ctk/clang/tooling.hpp"

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>

namespace ctk::clang_layer {
namespace {
TEST(ClangQuery, ParsesFixedQueryAndCopiesSemanticBindings) {
  const auto path =
      std::filesystem::temp_directory_path() / "ctk-native-query.cc";
  {
    std::ofstream output(path);
    output << "#include <vector>\n"
              "int target() { std::vector<int> values{7}; return "
              "values.front(); }\n"
              "int other() { return target(); }\n";
  }
  struct RemoveFile {
    std::filesystem::path path;
    ~RemoveFile() {
      std::error_code ignored;
      std::filesystem::remove(path, ignored);
    }
  } remove{path};

  auto engine = make_query_engine();
  FileInput file;
  file.path = path.string();
  file.working_directory = std::filesystem::current_path().string();
  file.compile_arguments = {"-std=c++20"};
  std::size_t matches = 0;
  SemanticBinding found;
  const auto result = engine->match(
      file,
      "functionDecl(isDefinition(), hasName(\"target\")).bind(\"function\")",
      [] { return true; },
      [&](const IQueryEngine::Bindings &bindings) {
        const auto item = bindings.find("function");
        if (item != bindings.end())
          found = item->second;
        ++matches;
      });

  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_FALSE(result.profile.empty());
  EXPECT_GT(result.native_memory_bytes, 0U);
  EXPECT_EQ(matches, 1U);
  EXPECT_EQ(found.kind, "FunctionDecl");
  EXPECT_EQ(found.name, "target");
  EXPECT_EQ(found.type, "int ()");
  ASSERT_TRUE(found.value.has_node());
  ASSERT_TRUE(found.value.node().has_function_decl());
  EXPECT_EQ(found.value.node()
                .function_decl()
                .function()
                .declarator()
                .value()
                .named()
                .name()
                .identifier(),
            "target");
  EXPECT_TRUE(found.value.is_complete());
  EXPECT_FALSE(found.value.node().function_decl().function().has_body());
}

TEST(ClangQuery, SerializesIntegerLiteralValueIntoItsConcretePayload) {
  const auto path =
      std::filesystem::temp_directory_path() / "ctk-native-literal.cc";
  {
    std::ofstream output(path);
    output << "int target() { return 42; }\n";
  }
  struct RemoveFile {
    std::filesystem::path path;
    ~RemoveFile() {
      std::error_code ignored;
      std::filesystem::remove(path, ignored);
    }
  } remove{path};

  auto engine = make_query_engine();
  const auto result = engine->match(
      {path.string(), {"-std=c++20"}, std::filesystem::current_path().string()},
      "integerLiteral().bind(\"literal\")", [] { return true; },
      [](const IQueryEngine::Bindings &bindings) {
        const auto &binding = bindings.at("literal").value;
        ASSERT_TRUE(binding.has_node());
        ASSERT_TRUE(binding.node().has_integer_literal());
        const auto &bits = binding.node().integer_literal().value();
        EXPECT_EQ(bits.unsigned_decimal(), "42");
        EXPECT_EQ(bits.bit_width(), 32U);
      });
  EXPECT_TRUE(result.ok) << result.message;
}

TEST(ClangQuery, BaseMatcherDispatchesToDerivedMemberCallSerializer) {
  const auto path =
      std::filesystem::temp_directory_path() / "ctk-native-derived-call.cc";
  {
    std::ofstream output(path);
    output << "struct Box { int get() { return 7; } };\n"
              "int target() { Box box; return box.get(); }\n";
  }
  struct RemoveFile {
    std::filesystem::path path;
    ~RemoveFile() {
      std::error_code ignored;
      std::filesystem::remove(path, ignored);
    }
  } remove{path};

  auto engine = make_query_engine();
  bool saw_member_call = false;
  const auto result = engine->match(
      {path.string(), {"-std=c++20"}, std::filesystem::current_path().string()},
      "callExpr().bind(\"call\")", [] { return true; },
      [&](const IQueryEngine::Bindings &bindings) {
        const auto &node = bindings.at("call").value.node();
        if (node.has_cxx_member_call_expr()) {
          const auto &member = node.cxx_member_call_expr();
          EXPECT_EQ(member.method_declaration().name(), "get");
          EXPECT_EQ(member.record_declaration().name(), "Box");
          EXPECT_FALSE(member.has_implicit_object_argument());
          EXPECT_TRUE(member.object_type().description().has_spelling());
          EXPECT_EQ(member.object_type().type().payload_case(),
                    ctk::ast::v1::TypeValue::PAYLOAD_NOT_SET);
          EXPECT_EQ(member.call().direct_callee().name(), "get");
          saw_member_call = true;
        }
      });
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_TRUE(saw_member_call);
}

TEST(ClangQuery, ReloadsValidatedNativeAstFromStorageAfterMemoryCacheReset) {
  const auto path =
      std::filesystem::temp_directory_path() / "ctk-native-storage-reload.cc";
  {
    std::ofstream output(path);
    output << "int target() { return 73; }\n";
  }
  struct RemoveFile {
    std::filesystem::path path;
    ~RemoveFile() {
      std::error_code ignored;
      std::filesystem::remove(path, ignored);
    }
  } remove{path};
  const FileInput file{path.string(), {"-std=c++20"},
                       std::filesystem::current_path().string()};
  const auto run = [&](const std::shared_ptr<IQueryEngine> &engine) {
    std::size_t matches = 0;
    const auto result = engine->match(
        file, "integerLiteral().bind(\"literal\")", [] { return true; },
        [&](const IQueryEngine::Bindings &) { ++matches; });
    EXPECT_TRUE(result.ok) << result.message;
    EXPECT_EQ(matches, 1U);
    return result;
  };
  (void)run(make_query_engine());
  const auto reloaded = run(make_query_engine());
  EXPECT_TRUE(reloaded.storage_hit) << reloaded.storage_message;
}

TEST(ClangQuery, DoesNotRetainMalformedTranslationUnits) {
  const auto path =
      std::filesystem::temp_directory_path() / "ctk-native-query-invalid.cc";
  {
    std::ofstream output(path);
    output << "#include <ctk_header_that_does_not_exist.hpp>\n"
              "int target( { return 7; }\n";
  }
  struct RemoveFile {
    std::filesystem::path path;
    ~RemoveFile() {
      std::error_code ignored;
      std::filesystem::remove(path, ignored);
    }
  } remove{path};

  auto engine = make_query_engine();
  FileInput file;
  file.path = path.string();
  file.working_directory = std::filesystem::current_path().string();
  const auto result = engine->match(
      file, "functionDecl().bind(\"decl\")", [] { return true; },
      [](const IQueryEngine::Bindings &) {});

  EXPECT_FALSE(result.ok);
  EXPECT_FALSE(result.snapshot_retained);
  EXPECT_EQ(result.native_memory_bytes, 0U);
  EXPECT_FALSE(result.message.empty());
}

TEST(ClangQuery, RefreshesCachedAstWhenMainFileOrHeaderChanges) {
  const auto original_working_directory = std::filesystem::current_path();
  const auto directory =
      std::filesystem::temp_directory_path() / "ctk-native-query-refresh";
  std::filesystem::create_directories(directory);
  struct RemoveDirectory {
    std::filesystem::path path;
    ~RemoveDirectory() {
      std::error_code ignored;
      std::filesystem::remove_all(path, ignored);
    }
  } remove{directory};
  struct RestoreWorkingDirectory {
    std::filesystem::path path;
    ~RestoreWorkingDirectory() {
      std::error_code ignored;
      std::filesystem::current_path(path, ignored);
    }
  } restore{original_working_directory};
  const auto header = directory / "values.hpp";
  const auto source = directory / "main.cc";
  {
    std::ofstream output(header);
    output << "inline int header_alpha() { return 1; }\n";
  }
  const auto header_time = std::filesystem::last_write_time(header);
  {
    std::ofstream output(source);
    output << "#include \"values.hpp\"\n"
              "int main_before() { return 0; }\n";
  }
  const auto source_time = std::filesystem::last_write_time(source);

  auto engine = make_query_engine();
  FileInput file;
  file.path = source.string();
  file.working_directory = directory.string();
  file.compile_arguments = {"-std=c++20"};
  const auto contains = [&](const std::string &name) {
    std::size_t found = 0;
    const auto result = engine->match(
        file, "functionDecl(hasName(\"" + name + "\")).bind(\"decl\")",
        [] { return true; },
        [&](const IQueryEngine::Bindings &bindings) {
          const auto binding = bindings.find("decl");
          if (binding != bindings.end() && binding->second.name == name)
            ++found;
        });
    EXPECT_TRUE(result.ok) << result.message;
    return found != 0;
  };

  EXPECT_TRUE(contains("header_alpha"));
  {
    std::ofstream output(header, std::ios::trunc);
    output << "inline int header_bravo() { return 2; }\n";
  }
  std::filesystem::last_write_time(header, header_time);
  EXPECT_TRUE(contains("header_bravo"));
  {
    std::ofstream output(source, std::ios::trunc);
    output << "#include \"values.hpp\"\n"
              "int main_after() { return 1; }\n";
  }
  std::filesystem::last_write_time(source, source_time);
  EXPECT_TRUE(contains("main_after"));
}

TEST(ClangQuery, DetectsEqualSizeSourceEditsWithPreservedTimestamp) {
  const auto path =
      std::filesystem::temp_directory_path() / "ctk-native-query-same-size.cc";
  {
    std::ofstream output(path);
    output << "int name_alpha() { return 1; }\n";
  }
  struct RemoveFile {
    std::filesystem::path path;
    ~RemoveFile() {
      std::error_code ignored;
      std::filesystem::remove(path, ignored);
    }
  } remove{path};
  const auto original_time = std::filesystem::last_write_time(path);
  auto engine = make_query_engine();
  FileInput file;
  file.path = path.string();
  file.working_directory = std::filesystem::current_path().string();
  file.compile_arguments = {"-std=c++20"};
  const auto contains = [&](const std::string &name) {
    bool found = false;
    const auto result = engine->match(
        file, "functionDecl(hasName(\"" + name + "\")).bind(\"decl\")",
        [] { return true; },
        [&](const IQueryEngine::Bindings &bindings) {
          const auto binding = bindings.find("decl");
          found = binding != bindings.end() && binding->second.name == name;
        });
    EXPECT_TRUE(result.ok) << result.message;
    return found;
  };
  ASSERT_TRUE(contains("name_alpha"));
  {
    std::ofstream output(path, std::ios::trunc);
    output << "int name_bravo() { return 2; }\n";
  }
  std::filesystem::last_write_time(path, original_time);
  EXPECT_TRUE(contains("name_bravo"));
}
} // namespace
} // namespace ctk::clang_layer
