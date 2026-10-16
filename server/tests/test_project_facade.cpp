#include "analysis/v1/call_graph_response.pb.h"
#include "analysis/v1/cfg_response.pb.h"
#include "ctk/clang/tooling.hpp"
#include "ctk/clang/call_graph_limits.hpp"
#include "ctk/platform/temporary_directory.hpp"
#include <fstream>
#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <gtest/gtest.h>
namespace ctk::clang_layer {
TEST(ProjectFacade,
     NativeDatabaseFlagsFeedMatchingCfgAndPerTranslationUnitCallGraphs) {
  ctk::platform::TemporaryDirectory directory{"ctk-project-facade"};
  std::ofstream(directory.path() / "fixture.cc") << "int f(){return VALUE;}";
  google::protobuf::ListValue commands;
  auto &command = *commands.add_values()->mutable_struct_value();
  (*command.mutable_fields())["directory"].set_string_value(
      directory.path().string());
  (*command.mutable_fields())["file"].set_string_value("fixture.cc");
  auto *arguments =
      (*command.mutable_fields())["arguments"].mutable_list_value();
  for (const auto *argument :
       {"clang++", "-std=c++20", "-DVALUE=23", "-c", "fixture.cc", "-o",
        "fixture.o", "-MMD", "-MF", "fixture.d"})
    arguments->add_values()->set_string_value(argument);
  std::string database;
  ASSERT_TRUE(
      google::protobuf::util::MessageToJsonString(commands, &database).ok());
  std::ofstream(directory.path() / "compile_commands.json") << database;
  Project project{directory.path().string(), {}};
  auto matches = match(project, "integerLiteral().bind(\"value\")");
  ASSERT_EQ(matches.size(), 1);
  ctk::match::v1::MatchResult row;
  ASSERT_TRUE(
      google::protobuf::util::JsonStringToMessage(matches.front(), &row).ok());
  EXPECT_EQ(row.bindings()
                .at("value")
                .node()
                .integer_literal()
                .value()
                .unsigned_decimal(),
            "23");
  ctk::analysis::v1::CfgResponse control_flow;
  ASSERT_TRUE(google::protobuf::util::JsonStringToMessage(cfg(project, "f"),
                                                          &control_flow)
                  .ok());
  ASSERT_EQ(control_flow.graphs_size(), 1);
  EXPECT_EQ(control_flow.graphs(0).function().qualified_name(), "f");
  google::protobuf::ListValue graphs;
  ASSERT_TRUE(
      google::protobuf::util::JsonStringToMessage(callgraph(project), &graphs)
          .ok());
  ASSERT_EQ(graphs.values_size(), 1);
  std::string graph_json;
  ASSERT_TRUE(
      google::protobuf::util::MessageToJsonString(graphs.values(0), &graph_json)
          .ok());
  ctk::analysis::v1::CallGraphResponse calls;
  ASSERT_TRUE(
      google::protobuf::util::JsonStringToMessage(graph_json, &calls).ok());
  ASSERT_EQ(calls.nodes_size(), 2);
  EXPECT_TRUE(calls.nodes(0).is_virtual_root());
  EXPECT_EQ(calls.nodes(1).function().qualified_name(), "f");
  EXPECT_FALSE(std::filesystem::exists(directory.path() / "fixture.o"));
  EXPECT_FALSE(std::filesystem::exists(directory.path() / "fixture.d"));
}
TEST(ProjectFacade, EmptyProjectsAndBadMatcherConstructionAreErrors) {
  EXPECT_THROW(match({}, "functionDecl()"), std::invalid_argument);
  EXPECT_THROW(cfg({}, "f"), std::invalid_argument);
  EXPECT_THROW(callgraph({}), std::invalid_argument);
  ctk::platform::TemporaryDirectory directory{"ctk-project-invalid"};
  const auto file = directory.path() / "fixture.cc";
  std::ofstream(file) << "int f(){return 7;}";
  const Project project{"", {file.string()}};
  EXPECT_THROW(match(project, "badMatcher()"), std::runtime_error);
  EXPECT_THROW(cfg(project, "missing"), std::runtime_error);
}
TEST(ProjectFacade, CallGraphNodeBudgetsRemainFiniteAcrossFilesOrUnlimited) {
  ctk::platform::TemporaryDirectory directory{"ctk-project-node-limits"};
  const auto first = directory.path() / "first.cc";
  const auto second = directory.path() / "second.cc";
  std::ofstream(first) << "void first(){}";
  std::ofstream(second) << "void second(){}";
  const Project project{"", {first.string(), second.string()}};
  CallGraphLimits limits{2, 100000, 4 * 1024 * 1024};
  EXPECT_THROW(callgraph(project, limits), std::runtime_error);
  for (const auto maximum : {std::uint64_t{4}, std::uint64_t{100001},
                             std::uint64_t{0}}) {
    limits.max_nodes = maximum;
    google::protobuf::ListValue graphs;
    ASSERT_TRUE(google::protobuf::util::JsonStringToMessage(
                    callgraph(project, limits), &graphs).ok());
    EXPECT_EQ(graphs.values_size(), 2);
    for (const auto &graph : graphs.values())
      EXPECT_EQ(graph.struct_value().fields().at("nodes").list_value().values_size(), 2);
  }
}
} // namespace ctk::clang_layer
