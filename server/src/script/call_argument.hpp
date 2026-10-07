#pragma once
#include <memory>
#include <string>
namespace ctk::script::detail {
struct Expression;
struct CallArgument {
  std::string name;
  std::shared_ptr<Expression> expression;
};
} // namespace ctk::script::detail
