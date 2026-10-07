#pragma once
#include "expression.hpp"
namespace ctk::script::detail {
struct Statement {
  enum class Kind { Assignment, Emission, Iteration };
  Kind kind = Kind::Emission;
  std::string name;
  std::shared_ptr<Expression> expression;
  std::vector<Statement> body;
};
} // namespace ctk::script::detail
