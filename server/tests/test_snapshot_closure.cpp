#include "ctk/clang/matching.hpp"
#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <gtest/gtest.h>
namespace ctk::clang_layer {
namespace {
class SnapshotClosure : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory directory{"ctk-snapshot-closure"};
  FileInput input{(directory.path() / "main.cc").string(),
                  {"-std=c++20"},
                  directory.path().string()};
  void write(const std::string &name, const std::string &source) {
    std::ofstream(directory.path() / name) << source;
  }
  int compile(const std::vector<std::string> &arguments) {
    auto quote = [](const std::string &value) {
      std::string result = "'";
      for (const auto character : value)
        result += character == '\'' ? "'\\''" : std::string(1, character);
      return result + "'";
    };
    std::string command = quote(CTK_TEST_CLANG_TOOL_PATH);
    for (const auto &argument : arguments)
      command += " " + quote(argument);
    return std::system(command.c_str());
  }
  void expect_persistent_literal(const std::string &value) {
    std::vector<std::string> literals;
    auto result = make_query_engine()->match(
        input, "integerLiteral().bind(\"n\")", [] { return true; },
        [&](const auto &rows) {
          literals.push_back(rows.at("n")
                                 .value.node()
                                 .integer_literal()
                                 .value()
                                 .unsigned_decimal());
        });
    ASSERT_TRUE(result.ok) << result.message;
    EXPECT_TRUE(result.storage_hit) << result.storage_message;
    EXPECT_NE(std::ranges::find(literals, value), literals.end());
  }
};
TEST_F(SnapshotClosure, CapturesHeadersAndReusesOnlyStronglyMatchingContent) {
  write("values.hpp", "inline int value(){return 7;}\n");
  write("main.cc", "#include \"values.hpp\"\nint f(){return value();}\n");
  auto engine = make_query_engine();
  auto first = engine->acquire_snapshot(input);
  ASSERT_TRUE(first->reusable);
  EXPECT_EQ(first, engine->acquire_snapshot(input));
  EXPECT_TRUE(std::any_of(first->inputs.begin(), first->inputs.end(),
                          [](const auto &i) {
                            return i.path.ends_with("values.hpp") &&
                                   i.kind == ctk::cache::InputKind::File;
                          }));
  const auto time =
      std::filesystem::last_write_time(directory.path() / "values.hpp");
  write("values.hpp", "inline int value(){return 9;}\n");
  std::filesystem::last_write_time(directory.path() / "values.hpp", time);
  auto changed = engine->acquire_snapshot(input);
  EXPECT_NE(first, changed);
  EXPECT_TRUE(changed->reusable);
  auto reloaded = make_query_engine()->match(
      input, "integerLiteral().bind(\"n\")", [] { return true; },
      [&](const auto &rows) {
        EXPECT_EQ(rows.at("n")
                      .value.node()
                      .integer_literal()
                      .value()
                      .unsigned_decimal(),
                  "9");
      });
  EXPECT_TRUE(reloaded.ok) << reloaded.message;
  EXPECT_TRUE(reloaded.storage_hit) << reloaded.storage_message;
}
TEST_F(SnapshotClosure,
       EarlierSearchCandidatesAndHasIncludeAbsenceAreValidated) {
  std::filesystem::create_directory(directory.path() / "first");
  std::filesystem::create_directory(directory.path() / "second");
  write("second/values.hpp", "int selected(){return 7;}\n");
  write("main.cc",
        "#include <values.hpp>\n#if __has_include(\"optional.hpp\")\n#include "
        "\"optional.hpp\"\n#endif\n");
  input.compile_arguments.insert(input.compile_arguments.end(),
                                 {"-I", (directory.path() / "first").string(),
                                  "-I",
                                  (directory.path() / "second").string()});
  auto engine = make_query_engine();
  auto original = engine->acquire_snapshot(input);
  ASSERT_TRUE(original->reusable);
  EXPECT_EQ(original, engine->acquire_snapshot(input));
  EXPECT_TRUE(std::any_of(original->inputs.begin(), original->inputs.end(),
                          [](const auto &i) {
                            return i.path.ends_with("first/values.hpp") &&
                                   i.kind == ctk::cache::InputKind::Absent;
                          }));
  write("first/values.hpp", "int earlier(){return 9;}\n");
  auto earlier = engine->acquire_snapshot(input);
  EXPECT_NE(original, earlier);
  write("optional.hpp", "int optional(){return 3;}\n");
  auto optional = engine->acquire_snapshot(input);
  EXPECT_NE(earlier, optional);
  std::size_t found = 0;
  auto result = engine->match(
      input, "functionDecl(hasName(\"optional\")).bind(\"f\")",
      [] { return true; }, [&](const auto &) { ++found; });
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_EQ(found, 1);
}
TEST_F(SnapshotClosure,
       PastedVolatileBuiltinsNeverEnterReusableMemoryOrStorage) {
  write("main.cc",
        "#define CAT(a,b) a##b\nconst char *value=CAT(__TI,ME__);\n");
  auto engine = make_query_engine();
  auto first = engine->acquire_snapshot(input);
  auto second = engine->acquire_snapshot(input);
  EXPECT_FALSE(first->reusable);
  EXPECT_FALSE(second->reusable);
  EXPECT_NE(first, second);
  auto result = make_query_engine()->match(
      input, "stringLiteral().bind(\"s\")", [] { return true; },
      [](const auto &) {});
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_FALSE(result.storage_hit);
}
TEST_F(SnapshotClosure, CapturesAndReloadsExplicitPchClosure) {
  write("values.hpp", "inline int value(){return 7;}\n");
  write("main.cc", "int f(){return value();}\n");
  const auto header = (directory.path() / "values.hpp").string();
  const auto pch = (directory.path() / "values.pch").string();
  ASSERT_EQ(
      compile({"-std=c++20", "-Xclang", "-fvalidate-ast-input-files-content",
               "-x", "c++-header", header, "-o", pch}),
      0);
  input.compile_arguments.insert(input.compile_arguments.end(),
                                 {"-include-pch", pch});
  auto engine = make_query_engine();
  auto first = engine->acquire_snapshot(input);
  ASSERT_TRUE(first->reusable);
  EXPECT_EQ(first, engine->acquire_snapshot(input));
  expect_persistent_literal("7");
  auto backend = make_match_backend();
  ctk::match::v1::MatchRequest request;
  request.set_query("functionDecl(hasName(\"f\")).bind(\"f\")");
  request.mutable_file()->set_file_path(input.path);
  request.mutable_file()->set_working_directory(input.working_directory);
  for (const auto &argument : input.compile_arguments)
    request.mutable_file()->add_compile_arguments(argument);
  auto pinned = backend->execute(request, {}, [] { return true; }, {});
  ASSERT_EQ(pinned.code, MatchCode::Ok) << pinned.message;
  ASSERT_TRUE(pinned.state);
  const auto time = std::filesystem::last_write_time(header);
  write("values.hpp", "inline int value(){return 9;}\n");
  std::filesystem::last_write_time(header, time);
  EXPECT_THROW(engine->acquire_snapshot(input), std::runtime_error);
  const auto pch_time = std::filesystem::last_write_time(pch);
  ASSERT_EQ(
      compile({"-std=c++20", "-Xclang", "-fvalidate-ast-input-files-content",
               "-x", "c++-header", header, "-o", pch}),
      0);
  std::filesystem::last_write_time(pch, pch_time);
  auto changed = engine->acquire_snapshot(input);
  EXPECT_NE(first, changed);
  expect_persistent_literal("9");
  request.clear_file();
  request.mutable_session()->set_session_id("pinned");
  request.set_query("integerLiteral().bind(\"n\")");
  auto old = backend->execute(request, pinned.state, [] { return true; }, {});
  ASSERT_EQ(old.code, MatchCode::Ok) << old.message;
  ASSERT_EQ(old.rows.size(), 1U);
  EXPECT_EQ(old.rows.front()
                .bindings()
                .at("n")
                .node()
                .integer_literal()
                .value()
                .unsigned_decimal(),
            "7");
}
TEST_F(SnapshotClosure, UnhashedPchRemainsAWorkingFreshNativeParse) {
  write("values.hpp", "inline int value(){return 7;}\n");
  write("main.cc", "int f(){return value();}\n");
  const auto header = (directory.path() / "values.hpp").string();
  const auto pch = (directory.path() / "values.pch").string();
  ASSERT_EQ(compile({"-std=c++20", "-x", "c++-header", header, "-o", pch}), 0);
  input.compile_arguments.insert(input.compile_arguments.end(),
                                 {"-include-pch", pch});
  auto engine = make_query_engine();
  auto first = engine->acquire_snapshot(input);
  EXPECT_FALSE(first->reusable);
  EXPECT_NE(first, engine->acquire_snapshot(input));
  auto result = engine->match(
      input, "integerLiteral()", [] { return true; }, [](const auto &) {});
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_FALSE(result.storage_hit);
}
TEST_F(SnapshotClosure,
       OversizedUncapturableClosureRemainsQueryableFromFreshParse) {
  constexpr std::size_t header_count = 16385;
  const auto headers = directory.path() / "headers";
  std::filesystem::create_directory(headers);
  std::ofstream main(directory.path() / "main.cc");
  for (std::size_t i = 0; i < header_count; ++i) {
    const auto name = "header_" + std::to_string(i) + ".hpp";
    main << "#include \"headers/" << name << "\"\n";
    std::ofstream(headers / name)
        << "inline int fallback_header_" << i << "() { return " << i << "; }\n";
  }
  main.close();

  std::size_t matches = 0;
  const auto result = make_query_engine()->match(
      input, "functionDecl(hasName(\"fallback_header_16384\")).bind(\"f\")",
      [] { return true; },
      [&](const auto &rows) {
        ASSERT_EQ(rows.size(), 2U);
        EXPECT_TRUE(rows.contains("root"));
        EXPECT_TRUE(rows.contains("f"));
        ++matches;
      });
  ASSERT_TRUE(result.ok) << result.message;
  EXPECT_FALSE(result.storage_hit);
  EXPECT_EQ(matches, 1U);
}
TEST_F(SnapshotClosure, NestedTimestampExpansionRemainsFresh) {
  write("main.cc",
        "#define CAT(a,b) a##b\nconst char *value=CAT(__TIME,STAMP__);\n");
  auto engine = make_query_engine();
  const auto first = engine->acquire_snapshot(input);
  EXPECT_FALSE(first->reusable);
  EXPECT_NE(first, engine->acquire_snapshot(input));
}
TEST_F(SnapshotClosure, SymlinkLookupRetargetingInvalidatesTheSnapshot) {
  write("one.hpp", "int one(){return 1;}\n");
  write("two.hpp", "int two(){return 2;}\n");
  std::filesystem::create_symlink("one.hpp", directory.path() / "selected.hpp");
  write("main.cc", "#include \"selected.hpp\"\n");
  auto engine = make_query_engine();
  const auto first = engine->acquire_snapshot(input);
  ASSERT_TRUE(first->reusable);
  std::filesystem::remove(directory.path() / "selected.hpp");
  std::filesystem::create_symlink("two.hpp", directory.path() / "selected.hpp");
  EXPECT_NE(first, engine->acquire_snapshot(input));
}
TEST_F(SnapshotClosure, UnsupportedMainOverlayPreservesNativeSemantics) {
  write("main.cc", "int value(){return 7;}\n");
  write("replacement.cc", "int value(){return 9;}\n");
  const auto overlay = (directory.path() / "overlay.json").string();
  write("overlay.json",
        "{\"version\":0,\"roots\":[{\"type\":\"file\",\"name\":\"" +
            input.path + "\",\"external-contents\":\"" +
            (directory.path() / "replacement.cc").string() + "\"}]}");
  input.compile_arguments.insert(input.compile_arguments.end(),
                                 {"-ivfsoverlay", overlay});
  auto engine = make_query_engine();
  auto first = engine->acquire_snapshot(input);
  EXPECT_FALSE(first->reusable);
  EXPECT_NE(first, engine->acquire_snapshot(input));
  std::vector<std::string> values;
  const auto result = engine->match(
      input, "integerLiteral().bind(\"n\")", [] { return true; },
      [&](const auto &rows) {
        values.push_back(rows.at("n")
                             .value.node()
                             .integer_literal()
                             .value()
                             .unsigned_decimal());
      });
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_FALSE(result.storage_hit);
  EXPECT_EQ(values, std::vector<std::string>{"9"});
}
TEST_F(SnapshotClosure, CapturesAndReloadsNamedModuleClosure) {
  write("base.cppm",
        "export module base; export int base_value(){return 7;}\n");
  write("numbers.cppm", "export module numbers; import base; export int "
                        "value(){return base_value();}\n");
  write("main.cc", "import numbers; int f(){return value();}\n");
  const auto base_source = (directory.path() / "base.cppm").string();
  const auto base_module = (directory.path() / "base.pcm").string();
  ASSERT_EQ(
      compile({"-std=c++20", "-Xclang", "-fvalidate-ast-input-files-content",
               "--precompile", base_source, "-o", base_module}),
      0);
  const auto source = (directory.path() / "numbers.cppm").string();
  const auto module = (directory.path() / "numbers.pcm").string();
  ASSERT_EQ(
      compile({"-std=c++20", "-Xclang", "-fvalidate-ast-input-files-content",
               "--precompile", "-fmodule-file=base=" + base_module, source,
               "-o", module}),
      0);
  input.compile_arguments.push_back("-fmodule-file=numbers=" + module);
  input.compile_arguments.push_back("-fmodule-file=base=" + base_module);
  auto engine = make_query_engine();
  auto first = engine->acquire_snapshot(input);
  ASSERT_TRUE(first->reusable);
  EXPECT_EQ(first, engine->acquire_snapshot(input));
  auto initial = engine->match(
      input, "integerLiteral()", [] { return true; }, [](const auto &) {});
  ASSERT_TRUE(initial.ok) << initial.message;
  expect_persistent_literal("7");
}
} // namespace
} // namespace ctk::clang_layer
