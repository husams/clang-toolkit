#include "variable_ranges.hpp"
#include "cfg_budget.hpp"
#include <algorithm>
#include <clang/AST/ASTContext.h>
#include <clang/AST/ExprCXX.h>
#include <clang/Analysis/CFG.h>
#include <deque>
#include <llvm/ADT/SmallString.h>

namespace ctk::clang_layer::control_flow {
namespace {
namespace pb = ctk::analysis::v1;
using Num = llvm::APInt;
using Usage = pb::VariableUsage;
// Native integers up to 128 bits, with room for exact intermediate sums.
constexpr unsigned bits = 256;
Num minimum(const Num &a, const Num &b) { return a.slt(b) ? a : b; }
Num maximum(const Num &a, const Num &b) { return a.sgt(b) ? a : b; }
struct Value {
  bool any{};
  Num lower{bits, 0}, upper{bits, 0};
  bool operator==(const Value &) const = default;
};
struct State {
  bool reachable{}, uninitialized{};
  Value value;
  bool operator==(const State &) const = default;
};
Value join(Value a, const Value &b) {
  if (!a.any)
    return b;
  if (!b.any)
    return a;
  return {true, minimum(a.lower, b.lower), maximum(a.upper, b.upper)};
}
State join(State a, const State &b) {
  if (!a.reachable)
    return b;
  if (!b.reachable)
    return a;
  return {true, a.uninitialized || b.uninitialized, join(a.value, b.value)};
}
std::string decimal(const Num &n) {
  llvm::SmallString<48> text;
  n.toString(text, 10, true);
  return std::string(text);
}
pb::VariableValueRange serialize(const State &state) {
  pb::VariableValueRange out;
  if (!state.reachable)
    out.set_kind(pb::VariableValueRange::UNREACHABLE);
  else if (!state.value.any)
    out.set_kind(pb::VariableValueRange::UNINITIALIZED);
  else {
    out.set_kind(pb::VariableValueRange::INTERVAL);
    out.set_lower(decimal(state.value.lower));
    out.set_upper(decimal(state.value.upper));
  }
  return out;
}
struct Arc {
  unsigned source, ordinal;
};
struct Depth {
  unsigned &value;
  explicit Depth(unsigned &depth) : value(depth) {
    if (value == 128)
      throw BuildFailure(MatchCode::ResourceExhausted,
                         "value interval expression depth exceeded");
    ++value;
  }
  ~Depth() { --value; }
};
struct Block {
  const clang::CFGBlock *native{};
  std::vector<Arc> incoming;
  std::vector<std::size_t> usages;
  State in, out;
  unsigned changes{};
};
struct Analysis {
  clang::ASTContext &ast;
  const clang::VarDecl &variable;
  const clang::CFG &graph;
  const std::vector<Usage> &usages;
  const std::vector<const clang::Stmt *> &statements;
  const std::function<void()> &step;
  std::vector<Block> blocks;
  VariableRanges result;
  std::uint64_t current_usage{};
  unsigned recursion{};

  void issue(const char *message, bool overflow, bool diagnose) {
    if (diagnose && (result.issue.empty() || (overflow && !result.overflow))) {
      result.issue = message;
      result.overflow = overflow;
      result.issue_usage = current_usage;
    }
  }
  Value type_value(clang::QualType type) {
    if (type.isNull() || !type->isIntegerType() || ast.getIntWidth(type) > 128)
      return {};
    auto width = ast.getIntWidth(type);
    if (type->isSignedIntegerType())
      return {true, Num::getSignedMinValue(width).sext(bits),
              Num::getSignedMaxValue(width).sext(bits)};
    return {true, Num(bits, 0), Num::getMaxValue(width).zext(bits)};
  }
  Value unknown_input(clang::QualType type, bool diagnose) {
    auto value = type_value(type);
    if (!value.any)
      issue("input type is outside the integer interval model", false,
            diagnose);
    return value;
  }
  Value convert(Value value, clang::QualType type, bool arithmetic,
                bool diagnose) {
    if (!value.any)
      return value;
    auto allowed = type_value(type);
    if (!allowed.any) {
      issue("numeric type is outside the integer interval model", false,
            diagnose);
      return type_value(variable.getType());
    }
    if (type->isBooleanType()) {
      const Num zero(bits, 0), one(bits, 1);
      if (value.upper.slt(zero) || value.lower.sgt(zero))
        return {true, one, one};
      return {true, zero,
              value.lower == zero && value.upper == zero ? zero : one};
    }
    if (value.lower.slt(allowed.lower) || value.upper.sgt(allowed.upper)) {
      if (!arithmetic || !type->isSignedIntegerType()) {
        issue("integer conversion or unsigned wrapping is outside the interval "
              "model",
              false, diagnose);
        return allowed;
      }
      issue("signed integer arithmetic may overflow", true, diagnose);
      // Propagate defined results; final diagnostics invalidate numeric claims
      // if overflow remains possible after widening and narrowing converge.
      value.lower = maximum(value.lower, allowed.lower);
      value.upper = minimum(value.upper, allowed.upper);
      value.any = value.lower.sle(value.upper);
    }
    return value;
  }
  Value arithmetic(Value lhs, Value rhs, bool subtract, clang::QualType type,
                   bool diagnose) {
    if (!lhs.any || !rhs.any)
      return {};
    Value out{true, subtract ? lhs.lower - rhs.upper : lhs.lower + rhs.lower,
              subtract ? lhs.upper - rhs.lower : lhs.upper + rhs.upper};
    return convert(out, type, true, diagnose);
  }
  Value evaluate(const clang::Expr *expr, const State &state, bool diagnose) {
    step();
    Depth depth(recursion);
    if (!expr)
      return {};
    if (auto *paren = llvm::dyn_cast<clang::ParenExpr>(expr))
      return evaluate(paren->getSubExpr(), state, diagnose);
    if (auto *constant = llvm::dyn_cast<clang::ConstantExpr>(expr))
      return evaluate(constant->getSubExpr(), state, diagnose);
    if (auto *literal = llvm::dyn_cast<clang::IntegerLiteral>(expr)) {
      if (literal->getValue().getBitWidth() <= 128) {
        auto n = literal->getValue().zext(bits);
        return {true, n, n};
      }
    }
    if (auto *literal = llvm::dyn_cast<clang::CXXBoolLiteralExpr>(expr)) {
      Num n(bits, literal->getValue());
      return {true, n, n};
    }
    if (auto *literal = llvm::dyn_cast<clang::CharacterLiteral>(expr)) {
      Num n(ast.getIntWidth(expr->getType()), literal->getValue());
      n = expr->getType()->isSignedIntegerType() ? n.sext(bits) : n.zext(bits);
      return {true, n, n};
    }
    if (auto *ref = llvm::dyn_cast<clang::DeclRefExpr>(expr)) {
      if (ref->getDecl() == &variable)
        return state.value;
      if (auto *constant =
              llvm::dyn_cast<clang::EnumConstantDecl>(ref->getDecl())) {
        auto n = constant->getInitVal().extOrTrunc(bits);
        return {true, n, n};
      }
      return unknown_input(expr->getType(), diagnose);
    }
    if (auto *cast = llvm::dyn_cast<clang::CastExpr>(expr)) {
      if (cast->getCastKind() == clang::CK_LValueToRValue ||
          cast->getCastKind() == clang::CK_NoOp ||
          cast->getCastKind() == clang::CK_IntegralCast ||
          cast->getCastKind() == clang::CK_IntegralToBoolean)
        return convert(evaluate(cast->getSubExpr(), state, diagnose),
                       expr->getType(), false, diagnose);
    }
    if (auto *unary = llvm::dyn_cast<clang::UnaryOperator>(expr)) {
      if (unary->getOpcode() == clang::UO_Plus)
        return convert(evaluate(unary->getSubExpr(), state, diagnose),
                       expr->getType(), true, diagnose);
      if (unary->getOpcode() == clang::UO_Minus)
        return arithmetic({true, Num(bits, 0), Num(bits, 0)},
                          evaluate(unary->getSubExpr(), state, diagnose), true,
                          expr->getType(), diagnose);
      if (unary->getOpcode() == clang::UO_LNot) {
        auto value = evaluate(unary->getSubExpr(), state, diagnose);
        if (!value.any)
          return value;
        const Num zero(bits, 0), one(bits, 1);
        if (value.lower == zero && value.upper == zero)
          return {true, one, one};
        return {true, zero,
                value.lower.sgt(zero) || value.upper.slt(zero) ? zero : one};
      }
    }
    if (auto *binary = llvm::dyn_cast<clang::BinaryOperator>(expr))
      if (binary->getOpcode() == clang::BO_Add ||
          binary->getOpcode() == clang::BO_Sub)
        return arithmetic(evaluate(binary->getLHS(), state, diagnose),
                          evaluate(binary->getRHS(), state, diagnose),
                          binary->getOpcode() == clang::BO_Sub, expr->getType(),
                          diagnose);
    if (llvm::isa<clang::CallExpr>(expr))
      return unknown_input(expr->getType(), diagnose);
    issue("expression is outside the integer interval model", false, diagnose);
    return type_value(expr->getType());
  }
  bool direct(const clang::Expr *expr) {
    step();
    Depth depth(recursion);
    if (!expr)
      return false;
    if (auto *paren = llvm::dyn_cast<clang::ParenExpr>(expr))
      return direct(paren->getSubExpr());
    if (auto *cast = llvm::dyn_cast<clang::CastExpr>(expr)) {
      auto source = type_value(cast->getSubExpr()->getType()),
           target = type_value(cast->getType());
      if (source.any && target.any && target.lower.sle(source.lower) &&
          target.upper.sge(source.upper))
        return direct(cast->getSubExpr());
      return false;
    }
    auto *ref = llvm::dyn_cast<clang::DeclRefExpr>(expr);
    return ref && ref->getDecl() == &variable;
  }
  State transfer(std::size_t index, State state, bool diagnose) {
    step();
    if (!state.reachable)
      return state;
    current_usage = usages[index].id();
    auto kind = usages[index].kind();
    const auto *stmt = statements[index];
    if (kind == Usage::DECLARE)
      return {true, true, {}};
    if (kind == Usage::READ) {
      state.uninitialized =
          false; // Only initialized executions have a numeric value.
    } else if (kind == Usage::INITIALIZE) {
      state.value = convert(evaluate(variable.getInit(), state, diagnose),
                            variable.getType(), false, diagnose);
      state.uninitialized = false;
    } else if (kind == Usage::WRITE) {
      auto *assignment = llvm::dyn_cast<clang::BinaryOperator>(stmt);
      if (!assignment) {
        issue("unmodeled numeric assignment", false, diagnose);
        state.value = type_value(variable.getType());
      } else
        state.value = convert(evaluate(assignment->getRHS(), state, diagnose),
                              variable.getType(), false, diagnose);
      state.uninitialized = false;
    } else if (kind == Usage::READ_WRITE) {
      if (auto *binary = llvm::dyn_cast<clang::CompoundAssignOperator>(stmt)) {
        if (binary->getOpcode() == clang::BO_AddAssign ||
            binary->getOpcode() == clang::BO_SubAssign) {
          auto lhs = convert(state.value, binary->getComputationLHSType(),
                             false, diagnose);
          state.value =
              arithmetic(lhs, evaluate(binary->getRHS(), state, diagnose),
                         binary->getOpcode() == clang::BO_SubAssign,
                         binary->getComputationResultType(), diagnose);
        } else {
          issue("compound operator is outside the interval model", false,
                diagnose);
          state.value = type_value(variable.getType());
        }
      } else if (auto *unary = llvm::dyn_cast<clang::UnaryOperator>(stmt)) {
        auto type = variable.getType();
        if (ast.isPromotableIntegerType(type))
          type = ast.getPromotedIntegerType(type);
        state.value =
            arithmetic(state.value, {true, Num(bits, 1), Num(bits, 1)},
                       unary->isDecrementOp(), type, diagnose);
      }
      state.value = convert(state.value, variable.getType(), false, diagnose);
      state.uninitialized = false;
    }
    state.reachable = state.uninitialized || state.value.any;
    return state;
  }
  State edge(const clang::CFGBlock &block, unsigned ordinal, State state) {
    step();
    auto *terminator = block.getTerminatorStmt();
    if (!state.value.any || block.succ_size() != 2 ||
        !llvm::isa_and_nonnull<clang::IfStmt, clang::WhileStmt, clang::ForStmt,
                               clang::DoStmt, clang::ConditionalOperator,
                               clang::BinaryOperator>(terminator))
      return state;
    // A logical terminator can contain the entire expression. Refine only
    // the operand actually tested by this block's outgoing edges.
    const auto *condition = block.getLastCondition();
    bool truth = ordinal == 0;
    while (condition) {
      condition = condition->IgnoreParens();
      if (auto *cast = llvm::dyn_cast<clang::ImplicitCastExpr>(condition)) {
        if (cast->getCastKind() == clang::CK_IntegralToBoolean) {
          condition = cast->getSubExpr();
          continue;
        }
      }
      auto *unary = llvm::dyn_cast<clang::UnaryOperator>(condition);
      if (!unary || unary->getOpcode() != clang::UO_LNot)
        break;
      truth = !truth;
      condition = unary->getSubExpr();
    }
    auto op = clang::BO_NE;
    Num constant(bits, 0);
    if (auto *comparison =
            llvm::dyn_cast_or_null<clang::BinaryOperator>(condition)) {
      if (!comparison->isComparisonOp())
        return state;
      op = comparison->getOpcode();
      bool reversed = false;
      const clang::Expr *other = nullptr;
      if (direct(comparison->getLHS()))
        other = comparison->getRHS();
      else if (direct(comparison->getRHS())) {
        other = comparison->getLHS();
        reversed = true;
      } else
        return state;
      const auto value = evaluate(other, {}, false);
      if (!value.any || value.lower != value.upper)
        return state;
      constant = value.lower;
      if (reversed) {
        if (op == clang::BO_LT)
          op = clang::BO_GT;
        else if (op == clang::BO_LE)
          op = clang::BO_GE;
        else if (op == clang::BO_GT)
          op = clang::BO_LT;
        else if (op == clang::BO_GE)
          op = clang::BO_LE;
      }
    } else if (!direct(condition))
      return state;
    if (!truth) {
      switch (op) {
      case clang::BO_LT:
        op = clang::BO_GE;
        break;
      case clang::BO_LE:
        op = clang::BO_GT;
        break;
      case clang::BO_GT:
        op = clang::BO_LE;
        break;
      case clang::BO_GE:
        op = clang::BO_LT;
        break;
      case clang::BO_EQ:
        op = clang::BO_NE;
        break;
      case clang::BO_NE:
        op = clang::BO_EQ;
        break;
      default:
        return state;
      }
    }
    auto &value = state.value;
    const Num one(bits, 1);
    switch (op) {
    case clang::BO_LT:
      value.upper = minimum(value.upper, constant - one);
      break;
    case clang::BO_LE:
      value.upper = minimum(value.upper, constant);
      break;
    case clang::BO_GT:
      value.lower = maximum(value.lower, constant + one);
      break;
    case clang::BO_GE:
      value.lower = maximum(value.lower, constant);
      break;
    case clang::BO_EQ:
      value.lower = maximum(value.lower, constant);
      value.upper = minimum(value.upper, constant);
      break;
    case clang::BO_NE:
      if (value.lower == constant)
        value.lower += one;
      if (value.upper == constant)
        value.upper -= one;
      break;
    default:
      break;
    }
    value.any = value.lower.sle(value.upper);
    state.reachable = value.any || state.uninitialized;
    return state;
  }
  bool mentions(const clang::Stmt *stmt) {
    if (!stmt)
      return false;
    step();
    Depth depth(recursion);
    if (auto *ref = llvm::dyn_cast<clang::DeclRefExpr>(stmt))
      if (ref->getDecl() == &variable)
        return true;
    for (auto *child : stmt->children())
      if (mentions(child))
        return true;
    return false;
  }
  State process(const Block &block, State state, bool diagnose) {
    if (!diagnose) {
      for (auto index : block.usages)
        state = transfer(index, state, false);
      return state;
    }
    // Check pure arithmetic at its CFG position too, e.g. use(x + 1),
    // even when the expression does not assign the selected variable.
    std::size_t cursor = 0;
    std::uint32_t element = 0;
    for (const auto &item : *block.native) {
      step();
      if (cursor < block.usages.size() &&
          usages[block.usages[cursor]].element() == element) {
        auto index = block.usages[cursor++];
        result.before[index] = serialize(state);
        state = transfer(index, state, true);
        result.after[index] = serialize(state);
      } else if (state.reachable) {
        if (auto stmt = item.getAs<clang::CFGStmt>()) {
          auto *expr = llvm::dyn_cast<clang::Expr>(stmt->getStmt());
          bool check = llvm::isa_and_nonnull<clang::CastExpr>(expr);
          if (auto *binary =
                  llvm::dyn_cast_or_null<clang::BinaryOperator>(expr))
            check = !binary->isAssignmentOp() && !binary->isComparisonOp() &&
                    !binary->isLogicalOp() &&
                    binary->getOpcode() != clang::BO_Comma;
          if (auto *unary = llvm::dyn_cast_or_null<clang::UnaryOperator>(expr))
            check = !unary->isIncrementDecrementOp() &&
                    unary->getOpcode() != clang::UO_AddrOf;
          if (check && mentions(expr))
            evaluate(expr, state, true);
        }
      }
      ++element;
    }
    return state;
  }
  void solve(bool widening) {
    std::deque<unsigned> pending;
    std::vector<bool> queued(blocks.size());
    auto queue = [&](unsigned id) {
      if (!queued[id]) {
        queued[id] = true;
        pending.push_back(id);
      }
    };
    if (widening)
      queue(graph.getEntry().getBlockID());
    else
      for (unsigned i = 0; i < blocks.size(); ++i)
        if (blocks[i].native)
          queue(i);
    auto limits = type_value(variable.getType());
    while (!pending.empty()) {
      step();
      auto id = pending.front();
      pending.pop_front();
      queued[id] = false;
      auto &block = blocks[id];
      State input;
      if (id == graph.getEntry().getBlockID())
        input = {true, true, {}};
      for (const auto &arc : block.incoming) {
        auto &from = blocks[arc.source];
        input = join(input, edge(*from.native, arc.ordinal, from.out));
      }
      block.in = input;
      auto output = process(block, input, false);
      if (widening) {
        output = join(block.out, output);
        if (++block.changes > 4 && block.out.value.any && output.value.any) {
          if (output.value.lower.slt(block.out.value.lower))
            output.value.lower = limits.lower;
          if (output.value.upper.sgt(block.out.value.upper))
            output.value.upper = limits.upper;
        }
      }
      if (output == block.out)
        continue;
      block.out = std::move(output);
      for (auto next : block.native->succs()) {
        step();
        if (auto *successor = next.getReachableBlock())
          queue(successor->getBlockID());
      }
    }
  }
  VariableRanges run() {
    result.before.resize(usages.size());
    result.after.resize(usages.size());
    auto type = variable.getType();
    if (!type->isSignedIntegerType() || ast.getIntWidth(type) > 128) {
      result.issue =
          "value intervals require a signed integer local of at most 128 bits";
    } else {
      blocks.resize(graph.getNumBlockIDs());
      for (auto *block : graph)
        blocks[block->getBlockID()].native = block;
      for (auto *block : graph) {
        unsigned ordinal = 0;
        for (auto next : block->succs()) {
          step();
          if (auto *successor = next.getReachableBlock())
            blocks[successor->getBlockID()].incoming.push_back(
                {block->getBlockID(), ordinal});
          ++ordinal;
        }
      }
      for (std::size_t i = 0; i < usages.size(); ++i)
        blocks[usages[i].block()].usages.push_back(i);
      solve(true);
      // Narrow from the sound widened post-fixpoint until stable. Work limits
      // and cancellation cover both phases; partial bounds are never emitted.
      solve(false);
      for (auto &block : blocks)
        if (block.native)
          process(block, block.in, true);
    }
    if (!result.issue.empty())
      for (auto *values : {&result.before, &result.after})
        for (auto &value : *values) {
          value.Clear();
          value.set_kind(pb::VariableValueRange::UNKNOWN);
        }
    return std::move(result);
  }
};
} // namespace
VariableRanges
variable_ranges(clang::ASTContext &ast, const clang::VarDecl &variable,
                const clang::CFG &graph, const std::vector<Usage> &usages,
                const std::vector<const clang::Stmt *> &statements,
                const std::function<void()> &step) {
  return Analysis{ast, variable, graph, usages, statements, step}.run();
}
} // namespace ctk::clang_layer::control_flow
