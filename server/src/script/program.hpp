#pragma once
#include "statement.hpp"
namespace ctk::script::detail {
struct Program {
  std::vector<Statement> statements;
};
Program parse(const std::string &source);
} // namespace ctk::script::detail
