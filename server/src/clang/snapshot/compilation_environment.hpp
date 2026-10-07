#pragma once
#include <string>
#include <utility>
#include <vector>
namespace ctk::clang_layer::snapshot {
std::vector<std::pair<std::string, std::string>> compilation_environment();
}
