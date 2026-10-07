#pragma once
#include "analysis/v1/script_scalar.pb.h"
#include "call_argument.hpp"
#include <optional>
#include <vector>
namespace ctk::script::detail {
struct ScopedBlock;
struct Expression {
  enum class Kind { Literal, Reference, Call, Parse, Match, Scoped };
  Kind kind = Kind::Literal;
  ctk::analysis::v1::ScriptScalar literal;
  std::string name;
  std::vector<CallArgument> arguments;
  std::shared_ptr<Expression> target;
  std::string binding;
  std::optional<std::size_t> row_index;
  std::shared_ptr<ScopedBlock> block;
};
} // namespace ctk::script::detail
