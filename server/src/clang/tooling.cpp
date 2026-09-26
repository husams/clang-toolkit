#include "ctk/clang/tooling.hpp"

#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/Tooling/Tooling.h>

namespace ctk::clang_layer {

std::vector<std::string> match(const Project&, const std::string&) { return {}; }
std::string cfg(const Project&, const std::string&) { return {}; }
std::string callgraph(const Project&) { return {}; }

}  // namespace ctk::clang_layer
