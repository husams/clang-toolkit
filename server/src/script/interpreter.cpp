#include "interpreter.hpp"
#include "ctk/script/error.hpp"
#include "scoped_block.hpp"
#include <unordered_set>
namespace ctk::script::detail {
using Code = ctk::clang_layer::MatchCode;
Interpreter::Interpreter(
    Environment *environment, Limits limits,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint)
    : environment_(environment), limits_(limits), checkpoint_(checkpoint),
      scopes_(1) {}
void Interpreter::tick() {
  if (!checkpoint_())
    throw Error(Code::Cancelled, "script cancelled");
  if (response_.executed_steps() >= limits_.max_steps)
    throw Error(Code::ResourceExhausted, "script step limit exceeded");
  response_.set_executed_steps(response_.executed_steps() + 1);
}
void Interpreter::retain(const Value &value) {
  if (!value.wire)
    throw Error(Code::Internal, "script function returned no value");
  values_.push_back(value.wire);
  if (value.bindings)
    bindings_.push_back(value.bindings);
  if (value.native_rows)
    rows_.push_back(value.native_rows);
  std::size_t bytes = response_.SpaceUsedLong();
  std::unordered_set<const void *> seen;
  auto inspect = [&](auto &list, const auto &size) {
    std::erase_if(list, [&](const auto &weak) {
      auto live = weak.lock();
      if (!live)
        return true;
      if (seen.insert(live.get()).second) {
        const auto amount = size(*live);
        if (bytes > limits_.max_retained_bytes ||
            amount > limits_.max_retained_bytes - bytes)
          throw Error(Code::ResourceExhausted,
                      "script retained-value limit exceeded");
        bytes += amount;
      }
      return false;
    });
  };
  inspect(values_, [](const auto &v) { return v.SpaceUsedLong(); });
  inspect(bindings_, [](const auto &v) { return v.retained_bytes(); });
  inspect(rows_,
          [](const auto &v) { return v.capacity() * sizeof(std::size_t); });
  if (bytes > limits_.max_retained_bytes)
    throw Error(Code::ResourceExhausted,
                "script retained-value limit exceeded");
}
Value Interpreter::row(const Value &value, std::size_t index) {
  if (!value.wire->has_matches() || !value.native_rows ||
      index >= static_cast<std::size_t>(value.wire->matches().rows_size()))
    throw Error(Code::InvalidArgument,
                "row requires matched rows and an in-range index");
  auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
  *wire->mutable_matches()->add_rows() =
      value.wire->matches().rows(static_cast<int>(index));
  Value result{wire, value.bindings,
               std::make_shared<const std::vector<std::size_t>>(
                   std::vector<std::size_t>{value.native_rows->at(index)})};
  retain(result);
  return result;
}
Value Interpreter::evaluate(const Expression &expression) {
  if (expression.kind == Expression::Kind::Literal) {
    auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
    *wire->mutable_scalar() = expression.literal;
    Value value{wire, {}, {}};
    retain(value);
    return value;
  }
  if (expression.kind == Expression::Kind::Reference) {
    for (auto scope = scopes_.rbegin(); scope != scopes_.rend(); ++scope)
      if (auto found = scope->find(expression.name); found != scope->end())
        return expression.row_index ? row(found->second, *expression.row_index)
                                    : found->second;
    throw Error(Code::InvalidArgument,
                "undefined script variable: " + expression.name);
  }
  tick();
  if (expression.kind == Expression::Kind::Scoped)
    return scoped(*expression.block);
  if (expression.kind == Expression::Kind::Parse ||
      expression.kind == Expression::Kind::Match) {
    if (!environment_)
      throw Error(Code::FailedPrecondition,
                  "native script operations require an environment");
    Value result;
    if (expression.kind == Expression::Kind::Parse)
      result = environment_->parse_file(expression.name);
    else {
      std::optional<Value> target;
      if (expression.target)
        target = evaluate(*expression.target);
      else if (!default_trees_.empty())
        target = default_trees_.back();
      result = environment_->match(expression.name, target ? &*target : nullptr,
                                   expression.binding);
    }
    retain(result);
    return result;
  }
  std::vector<Value> arguments;
  std::map<std::string, Value> options;
  for (const auto &argument : expression.arguments) {
    if (argument.name.empty()) {
      if (!options.empty())
        throw Error(Code::InvalidArgument,
                    "positional arguments must precede named arguments");
      arguments.push_back(evaluate(*argument.expression));
    } else {
      if (options.contains(argument.name))
        throw Error(Code::InvalidArgument,
                    "duplicate script option: " + argument.name);
      options.emplace(argument.name, evaluate(*argument.expression));
    }
  }
  if (expression.name == "row") {
    if (arguments.size() != 2 || !options.empty() ||
        !arguments[1].wire->has_scalar() ||
        arguments[1].wire->scalar().value_case() !=
            ctk::analysis::v1::ScriptScalar::kInteger ||
        arguments[1].wire->scalar().integer() < 0)
      throw Error(Code::InvalidArgument,
                  "row requires rows and a nonnegative integer index");
    return row(arguments[0], arguments[1].wire->scalar().integer());
  }
  Value result;
  if (expression.name == "count") {
    if (arguments.size() != 1 || !options.empty())
      throw Error(Code::InvalidArgument, "count requires one value");
    const auto &wire = *arguments[0].wire;
    std::int64_t count;
    if (wire.has_matches())
      count = wire.matches().rows_size();
    else if (wire.has_traversal())
      count = wire.traversal().nodes_size();
    else if (wire.has_cfg())
      count = wire.cfg().graphs_size();
    else if (wire.has_call_graph())
      count = wire.call_graph().nodes_size();
    else
      throw Error(Code::InvalidArgument,
                  "count requires an analysis collection");
    auto scalar = std::make_shared<ctk::analysis::v1::ScriptValue>();
    scalar->mutable_scalar()->set_integer(count);
    result.wire = scalar;
  } else {
    if (!environment_)
      throw Error(Code::FailedPrecondition,
                  "native script operations require a file target");
    if (expression.name == "match" && !default_trees_.empty() &&
        arguments.size() == 1 && arguments.front().wire->has_scalar() &&
        arguments.front().wire->scalar().value_case() ==
            ctk::analysis::v1::ScriptScalar::kText)
      result = environment_->match(arguments.front().wire->scalar().text(),
                                   &default_trees_.back(), {}, options);
    else
      result = environment_->call(expression.name, arguments, options);
  }
  retain(result);
  return result;
}
Value Interpreter::scoped(const ScopedBlock &block) {
  auto tree = evaluate(*block.target);
  if (!tree.wire || !tree.wire->has_tree() || !tree.bindings)
    throw Error(Code::InvalidArgument,
                "scoped script block requires a parsed native tree");
  scopes_.emplace_back();
  default_trees_.push_back(tree);
  Value result;
  try {
    statements(block.statements);
    tick();
    result = evaluate(*block.yielded);
  } catch (...) {
    default_trees_.pop_back();
    scopes_.pop_back();
    throw;
  }
  default_trees_.pop_back();
  scopes_.pop_back();
  retain(result);
  return result;
}
void Interpreter::statements(const std::vector<Statement> &body) {
  for (const auto &statement : body) {
    tick();
    auto value = evaluate(*statement.expression);
    if (statement.kind == Statement::Kind::Assignment) {
      if (scopes_.back().contains(statement.name))
        throw Error(Code::InvalidArgument,
                    "duplicate script variable: " + statement.name);
      scopes_.back().emplace(statement.name, std::move(value));
    } else if (statement.kind == Statement::Kind::Emission) {
      auto *emission = response_.add_emissions();
      if (statement.expression->kind == Expression::Kind::Reference)
        emission->set_name(statement.expression->name);
      *emission->mutable_value() = *value.wire;
      if (response_.ByteSizeLong() > limits_.max_response_bytes)
        throw Error(Code::ResourceExhausted,
                    "script response byte limit exceeded");
      retain(value);
    } else {
      if (!value.wire->has_matches())
        throw Error(Code::InvalidArgument, "foreach requires matched rows");
      for (int index = 0; index < value.wire->matches().rows_size(); ++index) {
        tick();
        scopes_.emplace_back();
        try {
          scopes_.back().emplace(statement.name, row(value, index));
          statements(statement.body);
        } catch (...) {
          scopes_.pop_back();
          throw;
        }
        scopes_.pop_back();
      }
    }
  }
}
ctk::analysis::v1::ScriptResponse Interpreter::run(const Program &program) {
  statements(program.statements);
  if (!checkpoint_())
    throw Error(Code::Cancelled, "script cancelled before publication");
  if (response_.ByteSizeLong() > limits_.max_response_bytes)
    throw Error(Code::ResourceExhausted, "script response byte limit exceeded");
  return std::move(response_);
}
} // namespace ctk::script::detail
