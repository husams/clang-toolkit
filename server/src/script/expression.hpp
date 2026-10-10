#pragma once
#include "analysis/v1/script_scalar.pb.h"
#include "call_argument.hpp"
#include <optional>
#include <cstdint>
#include <vector>
namespace ctk::script::detail {
struct ScopedBlock;
struct Expression {
  enum class Kind { Literal, Reference, Call, Parse, Match, Scoped, List,
                    Object, Member, Index, Files, Batch, Foreach, Group };
  Kind kind = Kind::Literal;
  ctk::analysis::v1::ScriptScalar literal;
  std::string name;
  std::vector<CallArgument> arguments;
  std::shared_ptr<Expression> target;
  std::string binding;
  std::optional<std::size_t> row_index;
  std::shared_ptr<ScopedBlock> block;
  std::vector<std::shared_ptr<Expression>> elements;
  std::vector<std::string> keys;
  std::string option;
  std::size_t count = 0;
  std::size_t jobs = 0;
  std::uint64_t memory_bytes = 0;
  bool continue_on_error = false;
  bool progress = false;
  std::shared_ptr<Expression> source;
  std::string iteration_name;
  std::shared_ptr<ScopedBlock> batch_body;
};
} // namespace ctk::script::detail
