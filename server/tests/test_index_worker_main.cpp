#include "ctk/platform/index_worker.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include "index/v1/index_service.pb.h"

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <gtest/gtest.h>
#include <optional>
#include <string>
#include <thread>

namespace {
namespace fs = std::filesystem;
using ctk::index::v1::IndexWorkerRequest;
using ctk::index::v1::IndexWorkerResponse;

class IndexWorkerMain : public ::testing::Test {
protected:
  ctk::platform::TemporaryDirectory temporary{"ctk-worker-main"};
  fs::path source = temporary.path() / "source.cpp";
  fs::path request_path = temporary.path() / "request.pb";
  fs::path result_path = temporary.path() / "result.pb";

  void SetUp() override {
    std::ofstream(source) << "int worker_symbol = 42;\n";
  }

  IndexWorkerRequest request() const {
    IndexWorkerRequest value;
    value.set_source(source.string());
    value.set_working_directory(temporary.path().string());
    value.add_compile_arguments("-std=c++20");
    return value;
  }

  int run(const IndexWorkerRequest &value, IndexWorkerResponse &response) {
    {
      std::ofstream output(request_path, std::ios::binary);
      if (!value.SerializeToOstream(&output)) {
        ADD_FAILURE() << "Cannot stage worker request";
        return -1;
      }
    }
    ctk::platform::IndexWorker worker(CTK_TEST_INDEX_WORKER, request_path,
                                      result_path);
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(30);
    std::optional<int> status;
    while (!(status = worker.poll()) &&
           std::chrono::steady_clock::now() < deadline)
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
    if (!status) {
      ADD_FAILURE() << "Worker did not finish";
      return -1;
    }
    std::ifstream input(result_path, std::ios::binary);
    EXPECT_TRUE(input && response.ParseFromIstream(&input))
        << "Worker exited " << *status << " without a structured response";
    return *status;
  }
};

TEST_F(IndexWorkerMain, ExtractsSymbolsWhenPriorityAdjustmentIsUnavailable) {
  IndexWorkerResponse response;
  ASSERT_EQ(run(request(), response), 0) << response.error();
  ASSERT_TRUE(response.success()) << response.error();
  EXPECT_TRUE(response.error().empty());
  EXPECT_TRUE(std::any_of(
      response.symbols().begin(), response.symbols().end(),
      [](const auto &symbol) { return symbol.name() == "worker_symbol"; }));
}

TEST_F(IndexWorkerMain, SerializesFilesystemExceptionInsteadOfAborting) {
  const auto include = temporary.path() / "not-a-directory";
  std::ofstream(include) << "This is a regular file, not an include directory.";
  auto value = request();
  value.add_compile_arguments("-I");
  value.add_compile_arguments(include.string());
  IndexWorkerResponse response;
  ASSERT_EQ(run(value, response), 1);
  EXPECT_FALSE(response.success());
  EXPECT_TRUE(response.symbols().empty());
  EXPECT_NE(response.error().find("index worker failed:"), std::string::npos);
  EXPECT_NE(response.error().find("not-a-directory"), std::string::npos);
}

TEST_F(IndexWorkerMain, ReturnsCompilationDatabaseFailureAsStructuredResponse) {
  IndexWorkerRequest value;
  value.set_list_translation_units(true);
  value.set_compile_commands_directory(temporary.path().string());
  IndexWorkerResponse response;
  ASSERT_EQ(run(value, response), 1);
  EXPECT_FALSE(response.success());
  EXPECT_FALSE(response.error().empty());
}
} // namespace
