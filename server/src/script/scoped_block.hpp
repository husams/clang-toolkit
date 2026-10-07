#pragma once
#include "statement.hpp"
namespace ctk::script::detail {
struct ScopedBlock {
  std::shared_ptr<Expression> target;
  std::vector<Statement> statements;
  std::shared_ptr<Expression> yielded;
};
} // namespace ctk::script::detail
