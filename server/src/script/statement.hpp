#pragma once
#include "expression.hpp"
namespace ctk::script::detail {
struct Statement {
  enum class Kind { Assignment, Emission, Iteration, Save, Value };
  Kind kind = Kind::Emission;
  std::string name;
  std::shared_ptr<Expression> expression;
  std::vector<Statement> body;
  std::shared_ptr<Expression> destination;
  std::string option;
};
} // namespace ctk::script::detail
