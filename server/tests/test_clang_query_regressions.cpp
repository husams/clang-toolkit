#include "ctk/clang/tooling.hpp"
#include "ctk/platform/temporary_directory.hpp"

#include <gtest/gtest.h>

#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <ranges>
#include <set>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace ctk::clang_layer {
namespace {

class TemporaryDirectory final {
public:
  explicit TemporaryDirectory(std::string_view suffix)
      : directory_("ctk-query-regression-" + std::string(suffix)) {}

  const std::filesystem::path &path() const noexcept {
    return directory_.path();
  }

private:
  ctk::platform::TemporaryDirectory directory_;
};

void write_file(const std::filesystem::path &path, std::string_view contents) {
  std::ofstream output(path, std::ios::binary | std::ios::trunc);
  output << contents;
  ASSERT_TRUE(output.good()) << path.string();
}

bool query_finds(const std::shared_ptr<IQueryEngine> &engine,
                 const FileInput &file, const std::string &name) {
  bool found = false;
  const auto result = engine->match(
      file, "functionDecl(hasName(\"" + name + "\")).bind(\"decl\")",
      [] { return true; },
      [&](const IQueryEngine::Bindings &bindings) {
        found = bindings.contains("decl");
      });
  EXPECT_TRUE(result.ok) << result.message;
  return found;
}

std::filesystem::path storage_root() {
  if (const auto *configured = std::getenv("CTK_STORAGE_ROOT");
      configured != nullptr && *configured != '\0')
    return configured;
  if (const auto *cache_home = std::getenv("XDG_CACHE_HOME");
      cache_home != nullptr && *cache_home != '\0')
    return std::filesystem::path(cache_home) / "clang-toolkit" / "storage";
  if (const auto *user_home = std::getenv("HOME");
      user_home != nullptr && *user_home != '\0')
    return std::filesystem::path(user_home) / ".cache" / "clang-toolkit" /
           "storage";
  return std::filesystem::temp_directory_path() / "clang-toolkit-storage";
}

std::set<std::filesystem::path> stored_blob_paths() {
  std::set<std::filesystem::path> paths;
  const auto root = storage_root() / "blobs";
  if (!std::filesystem::exists(root))
    return paths;
  for (const auto &entry :
       std::filesystem::recursive_directory_iterator(root)) {
    if (entry.is_regular_file() && entry.path().extension() == ".ast")
      paths.insert(entry.path());
  }
  return paths;
}

TEST(ClangQueryRegressions, TrigraphIncludeShadowingRefreshesBindings) {
  auto engine = make_query_engine();
  const std::vector<std::pair<std::string, bool>> directive_spellings = {
      {"?"
       "?=include <selected.hpp>\n",
       true},
      {"%"
       "\\"
       "\n:include <selected.hpp>\n",
       false},
      {"%"
       "?"
       "?/\n:include <selected.hpp>\n",
       true},
  };
  for (std::size_t index = 0; index < directive_spellings.size(); ++index) {
    TemporaryDirectory directory("split-digraph-shadow");
    const auto earlier = directory.path() / "earlier";
    const auto later = directory.path() / "later";
    std::filesystem::create_directories(earlier);
    std::filesystem::create_directories(later);
    write_file(later / "selected.hpp",
               "inline int prior_header() { return 1; }\n");
    const auto source = directory.path() / "main.cc";
    write_file(source, directive_spellings[index].first +
                           "int main_function() { return 0; }\n");

    std::vector<std::string> arguments = {"-std=c++20", "-I" + earlier.string(),
                                          "-I" + later.string()};
    if (directive_spellings[index].second)
      arguments.emplace_back("-trigraphs");
    const FileInput file{source.string(), std::move(arguments),
                         directory.path().string()};
    EXPECT_TRUE(query_finds(engine, file, "prior_header")) << index;
    EXPECT_FALSE(query_finds(engine, file, "shadow_header")) << index;

    write_file(earlier / "selected.hpp",
               "inline int shadow_header() { return 2; }\n");
    EXPECT_TRUE(query_finds(engine, file, "shadow_header")) << index;
    EXPECT_FALSE(query_finds(engine, file, "prior_header")) << index;
  }
}

TEST(ClangQueryRegressions, EphemeralSnapshotsAreFreshAndActuallyRetained) {
  TemporaryDirectory directory("ephemeral");
  const auto source = directory.path() / "main.cc";
  write_file(source,
             "#define VERSION 1\nint first_version() { return VERSION; }\n");

  auto engine = make_query_engine();
  const FileInput file{
      source.string(), {"-std=c++20"}, directory.path().string()};
  auto result = engine->match(
      file, "functionDecl(hasName(\"first_version\")).bind(\"decl\")",
      [] { return true; }, [](const IQueryEngine::Bindings &) {});
  ASSERT_TRUE(result.ok) << result.message;
  EXPECT_TRUE(result.snapshot_retained);

  write_file(source,
             "#define VERSION 2\nint second_version() { return VERSION; }\n");
  result = engine->match(
      file, "functionDecl(hasName(\"second_version\")).bind(\"decl\")",
      [] { return true; }, [](const IQueryEngine::Bindings &) {});
  ASSERT_TRUE(result.ok) << result.message;
  EXPECT_TRUE(result.snapshot_retained);
  EXPECT_FALSE(query_finds(engine, file, "first_version"));
}

TEST(ClangQueryRegressions, CorruptStoredArtifactFallsBackToSourceParsing) {
  TemporaryDirectory directory("corrupt-artifact");
  const auto source = directory.path() / "main.cc";
  write_file(source, "int corrupt_artifact_target() { return 319; }\n");
  const FileInput file{
      source.string(), {"-std=c++20"}, directory.path().string()};

  const auto before = stored_blob_paths();
  auto initial_engine = make_query_engine();
  auto result = initial_engine->match(
      file, "functionDecl(hasName(\"corrupt_artifact_target\")).bind(\"decl\")",
      [] { return true; }, [](const IQueryEngine::Bindings &) {});
  ASSERT_TRUE(result.ok) << result.message;
  const auto after = stored_blob_paths();
  std::vector<std::filesystem::path> created;
  std::ranges::set_difference(after, before, std::back_inserter(created));
  ASSERT_EQ(created.size(), 1U)
      << "expected the initial query to publish one native artifact";

  std::ifstream original_input(created.front(), std::ios::binary);
  ASSERT_TRUE(original_input.good());
  const std::string original_bytes(
      (std::istreambuf_iterator<char>(original_input)), {});
  struct RestoreBlob {
    std::filesystem::path path;
    std::string bytes;
    ~RestoreBlob() {
      std::ofstream output(path, std::ios::binary | std::ios::trunc);
      output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
    }
  } restore{created.front(), original_bytes};

  {
    std::ofstream corrupt(created.front(), std::ios::binary | std::ios::trunc);
    ASSERT_TRUE(corrupt.good());
    corrupt << "corrupt artifact";
    ASSERT_TRUE(corrupt.good());
  }

  auto reload_engine = make_query_engine();
  result = reload_engine->match(
      file, "functionDecl(hasName(\"corrupt_artifact_target\")).bind(\"decl\")",
      [] { return true; }, [](const IQueryEngine::Bindings &) {});
  EXPECT_TRUE(result.ok) << result.message;
  EXPECT_FALSE(result.storage_hit);
}

std::set<std::filesystem::path> staged_artifact_directories() {
  std::set<std::filesystem::path> paths;
  for (const auto &entry : std::filesystem::directory_iterator(
           std::filesystem::temp_directory_path())) {
    if (!entry.path().filename().string().starts_with("ctk-native-ast-"))
      continue;
    std::error_code error;
    if (std::filesystem::exists(entry.path() / "artifact.ast", error))
      paths.insert(entry.path());
  }
  return paths;
}

TEST(ClangQueryRegressions,
     SessionPinKeepsLoadedArtifactUntilEngineDestruction) {
  TemporaryDirectory directory("pin-lifetime");
  const auto source = directory.path() / "main.cc";
  write_file(source, "int pinned_target() { return 11; }\n");
  const FileInput file{
      source.string(), {"-std=c++20"}, directory.path().string()};
  ASSERT_TRUE(query_finds(make_query_engine(), file, "pinned_target"));

  const auto before = staged_artifact_directories();
  auto engine = make_query_engine();
  const auto loaded = engine->match(
      file, "functionDecl().bind(\"decl\")", [] { return true; },
      [](const IQueryEngine::Bindings &) {});
  ASSERT_TRUE(loaded.ok) << loaded.message;
  ASSERT_TRUE(loaded.storage_hit) << loaded.storage_message;
  const auto after = staged_artifact_directories();
  std::vector<std::filesystem::path> created;
  std::ranges::set_difference(after, before, std::back_inserter(created));
  ASSERT_EQ(created.size(), 1U);

  // More distinct reusable snapshots than the cache's 64-entry LRU capacity.
  for (std::size_t index = 0; index < 65; ++index) {
    const auto other = directory.path() / (std::to_string(index) + ".cc");
    write_file(other, "int additional_target() { return 22; }\n");
    ASSERT_TRUE(query_finds(
        engine, {other.string(), {"-std=c++20"}, directory.path().string()},
        "additional_target"));
  }
  EXPECT_TRUE(std::filesystem::exists(created.front() / "artifact.ast"));
  engine.reset();
  EXPECT_FALSE(std::filesystem::exists(created.front()));
}

} // namespace
} // namespace ctk::clang_layer
