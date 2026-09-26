#pragma once

#include <string>
#include <vector>

namespace ctk::clang_layer {

// Thin wrapper over Clang C++ APIs: AST matchers, RecursiveASTVisitor
// traversal, CFG construction and call-graph building.
struct Project {
  std::string compile_commands_dir;
  std::vector<std::string> files;
};

std::vector<std::string> match(const Project& project, const std::string& matcher);
std::string cfg(const Project& project, const std::string& function);
std::string callgraph(const Project& project);

}  // namespace ctk::clang_layer
