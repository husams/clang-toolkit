#include "ctk/platform/temporary_directory.hpp"

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>

namespace ctk::platform {
namespace {

TEST(TemporaryDirectory, IsolatesArtifactsAndRemovesThemWithTheirOwner) {
  std::filesystem::path first_path;
  {
    TemporaryDirectory first("ctk-private-artifact-test");
    TemporaryDirectory second("ctk-private-artifact-test");
    first_path = first.path();
    EXPECT_NE(first.path(), second.path());
    const auto permissions =
        std::filesystem::status(first.path()).permissions();
    EXPECT_EQ(permissions & std::filesystem::perms::all,
              std::filesystem::perms::owner_all);
    {
      std::ofstream output(first.path() / "artifact.ast");
      output << "first artifact";
    }
    EXPECT_TRUE(std::filesystem::exists(first.path() / "artifact.ast"));
    EXPECT_FALSE(std::filesystem::exists(second.path() / "artifact.ast"));
  }
  EXPECT_FALSE(std::filesystem::exists(first_path));
}

} // namespace
} // namespace ctk::platform
