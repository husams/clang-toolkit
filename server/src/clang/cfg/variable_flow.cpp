#include "variable_flow.hpp"
#include "../captured_binding_state.hpp"
#include "../native_snapshot_owner.hpp"
#include "cfg_budget.hpp"
#include "variable_ranges.hpp"
#include <algorithm>
#include <clang/AST/ExprCXX.h>
#include <clang/AST/ParentMapContext.h>
#include <clang/AST/StmtCXX.h>
#include <clang/Analysis/CFG.h>
#include <deque>
#include <set>
#include <vector>

namespace ctk::clang_layer::control_flow {
namespace {
namespace pb = ctk::analysis::v1;
using Usage = pb::VariableUsage;
using Definitions = std::set<std::uint64_t>;
bool reads(Usage::Kind kind) {
  return kind == Usage::READ || kind == Usage::READ_WRITE;
}
bool writes(Usage::Kind kind) {
  return kind == Usage::INITIALIZE || kind == Usage::WRITE ||
         kind == Usage::READ_WRITE;
}
const clang::DynTypedNode &
selected(const NativeBindingState &state,
         const ctk::match::v1::BindingMatchTarget &target) {
  auto *captured = dynamic_cast<const CapturedBindingState *>(&state);
  if (!captured)
    throw BuildFailure(MatchCode::FailedPrecondition,
                       "native bindings unavailable");
  const clang::DynTypedNode *node = nullptr;
  for (std::size_t i = 0; i < captured->rows.size(); ++i) {
    if (target.has_match_index() && i != target.match_index())
      continue;
    auto found = captured->rows[i].find(target.bind());
    if (found == captured->rows[i].end())
      continue;
    if (node)
      throw BuildFailure(MatchCode::InvalidArgument,
                         "select exactly one variable and function row");
    node = &found->second;
  }
  if (!node)
    throw BuildFailure(MatchCode::NotFound, "binding or row unavailable");
  return *node;
}
void location(clang::SourceLocation source, clang::ASTContext &ast,
              pb::VariableFlowLocation &output) {
  auto loc = ast.getSourceManager().getPresumedLoc(source);
  if (loc.isInvalid())
    throw BuildFailure(MatchCode::FailedPrecondition,
                       "variable source location unavailable");
  output.set_file(loc.getFilename());
  output.set_line(loc.getLine());
  output.set_column(loc.getColumn());
}
struct Block {
  const clang::CFGBlock *native{};
  std::vector<std::size_t> usages;
  Definitions in, out;
  bool reachable{}, live_in{}, live_out{};
};
struct Analysis {
  clang::ASTContext &ast;
  const clang::VarDecl &variable;
  const clang::CFG &graph;
  IMatchBackend::Checkpoint checkpoint;
  ICfgBackend::VariableSink sink;
  std::size_t max_events, max_iterations, max_bytes, iterations{}, scanned{},
      emitted{};
  std::vector<Block> blocks;
  std::vector<Usage> usages;
  std::string unsupported;
  std::vector<const clang::Stmt *> usage_statements;
  bool value_intervals{};
  VariableRanges ranges;
  void check() const {
    if (checkpoint && !checkpoint())
      throw BuildFailure(MatchCode::Cancelled, "variable flow cancelled");
  }
  void step() {
    check();
    if (++iterations > max_iterations)
      throw BuildFailure(MatchCode::ResourceExhausted,
                         "variable flow convergence/work limit exceeded");
  }
  void emit(const pb::VariableFlowEvent &event) {
    check();
    if (++emitted > max_events)
      throw BuildFailure(MatchCode::ResourceExhausted,
                         "variable flow event count limit exceeded");
    if (event.ByteSizeLong() > max_bytes)
      throw BuildFailure(MatchCode::ResourceExhausted,
                         "variable flow event byte limit exceeded");
    std::string message;
    auto code = sink(event, message);
    if (code != MatchCode::Ok)
      throw BuildFailure(code, message.empty() ? "variable flow stream closed"
                                               : message.c_str());
  }
  bool refers(const clang::Expr *expression) const {
    expression = expression ? expression->IgnoreParenImpCasts() : nullptr;
    if (auto *assignment =
            llvm::dyn_cast_or_null<clang::BinaryOperator>(expression))
      if (assignment->isAssignmentOp() && assignment->isLValue())
        return refers(assignment->getLHS());
    if (auto *unary = llvm::dyn_cast_or_null<clang::UnaryOperator>(expression))
      if (unary->isIncrementDecrementOp() && unary->isLValue())
        return refers(unary->getSubExpr());
    auto *reference = llvm::dyn_cast_or_null<clang::DeclRefExpr>(expression);
    return reference && reference->getDecl() == &variable;
  }
  // Only inspect the current expression's direct AST semantics; child CFG
  // elements account for their own reads and writes, exactly once.
  bool known_reference(const clang::Expr &reference) {
    const clang::Stmt *node = &reference;
    for (;;) {
      auto parents = ast.getParents(*node);
      if (parents.size() != 1)
        return false;
      auto *parent = parents[0].get<clang::Stmt>();
      if (!parent)
        return false;
      if (llvm::isa<clang::CompoundStmt>(parent)) {
        // GNU statement-expression bodies can export their last lvalue.
        for (const auto &outer : ast.getParents(*parent))
          if (outer.get<clang::StmtExpr>())
            return false;
        return true; // Discarded non-volatile lvalue; no escape or value read.
      }
      if (auto *branch = llvm::dyn_cast<clang::IfStmt>(parent))
        return branch->getThen() == node || branch->getElse() == node;
      if (auto *loop = llvm::dyn_cast<clang::WhileStmt>(parent))
        return loop->getBody() == node;
      if (auto *loop = llvm::dyn_cast<clang::DoStmt>(parent))
        return loop->getBody() == node;
      if (auto *loop = llvm::dyn_cast<clang::CXXForRangeStmt>(parent))
        return loop->getBody() == node;
      if (auto *branch = llvm::dyn_cast<clang::SwitchStmt>(parent))
        return branch->getBody() == node;
      if (auto *label = llvm::dyn_cast<clang::LabelStmt>(parent))
        return label->getSubStmt() == node;
      if (auto *label = llvm::dyn_cast<clang::CaseStmt>(parent))
        return label->getSubStmt() == node;
      if (auto *label = llvm::dyn_cast<clang::DefaultStmt>(parent))
        return label->getSubStmt() == node;
      if (auto *attribute = llvm::dyn_cast<clang::AttributedStmt>(parent))
        return attribute->getSubStmt() == node;
      if (auto *loop = llvm::dyn_cast<clang::ForStmt>(parent))
        return loop->getCond() != node;
      if (llvm::isa<clang::ParenExpr>(parent)) {
        node = parent;
        continue;
      }
      if (auto *cast = llvm::dyn_cast<clang::ImplicitCastExpr>(parent)) {
        // C++23 implicit move inserts a no-op lvalue-to-xvalue cast before
        // loading a returned scalar; it preserves this declaration identity.
        if (cast->getCastKind() == clang::CK_NoOp) {
          node = parent;
          continue;
        }
        return cast->getCastKind() == clang::CK_LValueToRValue;
      }
      if (auto *binary = llvm::dyn_cast<clang::BinaryOperator>(parent))
        return binary->isAssignmentOp() && refers(binary->getLHS());
      if (auto *unary = llvm::dyn_cast<clang::UnaryOperator>(parent))
        return unary->isIncrementDecrementOp() ||
               unary->getOpcode() == clang::UO_AddrOf;
      return false;
    }
  }
  struct Effects {
    bool reference{}, mutation{};
  };
  Effects effects(const clang::Stmt *node) {
    if (!node)
      return {};
    step();
    Effects result;
    if (auto *reference = llvm::dyn_cast<clang::DeclRefExpr>(node))
      result.reference = reference->getDecl() == &variable;
    if (auto *unary = llvm::dyn_cast<clang::UnaryOperator>(node))
      result.mutation =
          unary->isIncrementDecrementOp() && refers(unary->getSubExpr());
    if (auto *binary = llvm::dyn_cast<clang::BinaryOperator>(node))
      result.mutation = binary->isAssignmentOp() && refers(binary->getLHS());
    for (auto *child : node->children()) {
      auto value = effects(child);
      result.reference |= value.reference;
      result.mutation |= value.mutation;
    }
    return result;
  }
  Usage::Kind classify(const clang::Stmt *stmt) {
    // Assignment and prefix-increment results are themselves lvalues. Their
    // result can bind a reference even when the original DeclRefExpr is only
    // the valid operand of a write, e.g. touch(++x) or int &r = (x = 1).
    if (auto *expression = llvm::dyn_cast<clang::Expr>(stmt))
      if (expression->isGLValue() && refers(expression) &&
          !known_reference(*expression))
        unsupported = "reference binding or unmodeled variable use";
    if (auto *declaration = llvm::dyn_cast<clang::DeclStmt>(stmt)) {
      for (auto *decl : declaration->decls())
        if (decl == &variable)
          return variable.hasInit() ? Usage::INITIALIZE : Usage::DECLARE;
    }
    if (auto *cast = llvm::dyn_cast<clang::ImplicitCastExpr>(stmt))
      if (cast->getCastKind() == clang::CK_LValueToRValue &&
          refers(cast->getSubExpr()))
        return Usage::READ;
    if (auto *binary = llvm::dyn_cast<clang::BinaryOperator>(stmt)) {
      if (binary->isAssignmentOp() && !ast.getLangOpts().CPlusPlus17) {
        auto lhs = effects(binary->getLHS()), rhs = effects(binary->getRHS());
        if (lhs.reference && rhs.reference && (lhs.mutation || rhs.mutation))
          unsupported = "unsequenced assignment effects are unsupported in "
                        "this language mode";
      }
      if (binary->isAssignmentOp() && refers(binary->getLHS()))
        return binary->isCompoundAssignmentOp() ? Usage::READ_WRITE
                                                : Usage::WRITE;
      if (!binary->isAssignmentOp() && binary->getOpcode() != clang::BO_Comma &&
          !binary->isLogicalOp()) {
        auto lhs = effects(binary->getLHS()), rhs = effects(binary->getRHS());
        if (lhs.reference && rhs.reference && (lhs.mutation || rhs.mutation))
          unsupported = "unsequenced variable effects are unsupported";
      }
    }
    if (auto *unary = llvm::dyn_cast<clang::UnaryOperator>(stmt)) {
      if (refers(unary->getSubExpr())) {
        if (unary->isIncrementDecrementOp())
          return Usage::READ_WRITE;
        if (unary->getOpcode() == clang::UO_AddrOf) {
          unsupported = "variable address escapes the direct scalar model";
          return Usage::ADDRESS_TAKEN;
        }
      }
    }
    if (auto *reference = llvm::dyn_cast<clang::DeclRefExpr>(stmt))
      if (reference->getDecl() == &variable && !known_reference(*reference)) {
        unsupported = "reference binding or unmodeled variable use";
        return Usage::UNKNOWN_EFFECT;
      }
    if (auto *lambda = llvm::dyn_cast<clang::LambdaExpr>(stmt))
      for (const auto &capture : lambda->captures())
        if (capture.capturesVariable() &&
            capture.getCapturedVar() == &variable) {
          unsupported = "captured variables are unsupported";
          return Usage::UNKNOWN_EFFECT;
        }
    if (auto *call = llvm::dyn_cast<clang::CallExpr>(stmt)) {
      auto *callee = call->getDirectCallee();
      if (!callee)
        unsupported = "indirect call effects are unsupported";
      else {
        auto name = callee->getNameAsString();
        if (callee->hasAttr<clang::ReturnsTwiceAttr>() || name == "setjmp" ||
            name == "_setjmp" || name == "sigsetjmp" || name == "__sigsetjmp" ||
            name == "longjmp" || name == "_longjmp" || name == "siglongjmp" ||
            name == "__builtin_setjmp" || name == "__builtin_longjmp")
          unsupported = "non-local jump effects are unsupported";
      }
      Effects previous;
      for (auto *argument : call->arguments()) {
        auto current = effects(argument);
        if (previous.reference && current.reference &&
            (previous.mutation || current.mutation))
          unsupported = "unspecified argument evaluation order is unsupported";
        previous.reference |= current.reference;
        previous.mutation |= current.mutation;
      }
    }
    if (llvm::isa<clang::AsmStmt, clang::CXXThrowExpr,
                  clang::CoroutineSuspendExpr>(stmt))
      unsupported = "assembly, exception or coroutine effects are unsupported";
    return Usage::KIND_UNSPECIFIED;
  }
  void classify() {
    blocks.resize(graph.getNumBlockIDs());
    for (auto *block : graph)
      blocks[block->getBlockID()].native = block;
    for (std::size_t index = 0; index < blocks.size(); ++index) {
      auto &block = blocks[index];
      if (!block.native)
        continue;
      std::uint32_t element = 0;
      for (const auto &item : *block.native) {
        check();
        if (++scanned > 1000000)
          throw BuildFailure(MatchCode::ResourceExhausted,
                             "variable flow CFG element limit exceeded");
        if (auto statement = item.getAs<clang::CFGStmt>()) {
          auto kind = classify(statement->getStmt());
          if (kind != Usage::KIND_UNSPECIFIED) {
            if (usages.size() == max_events)
              throw BuildFailure(MatchCode::ResourceExhausted,
                                 "variable flow usage limit exceeded");
            Usage value;
            value.set_id(usages.size() + 1);
            value.set_block(index);
            value.set_element(element);
            value.set_kind(kind);
            value.set_provisional(true);
            auto loc = kind == Usage::DECLARE || kind == Usage::INITIALIZE
                           ? variable.getLocation()
                           : statement->getStmt()->getBeginLoc();
            location(loc, ast, *value.mutable_location());
            block.usages.push_back(usages.size());
            usages.push_back(value);
            usage_statements.push_back(statement->getStmt());
            pb::VariableFlowEvent event;
            event.mutable_usage()->CopyFrom(value);
            emit(event);
          }
        }
        ++element;
      }
    }
  }
  static void transfer(const Usage &usage, Definitions &state) {
    if (usage.kind() == Usage::DECLARE)
      state = {0};
    else if (writes(usage.kind()))
      state = {usage.id()};
  }
  void converge() {
    std::deque<unsigned> pending{graph.getEntry().getBlockID()};
    std::vector<bool> queued(blocks.size());
    queued[pending.front()] = true;
    std::size_t cells = 0;
    while (!pending.empty()) {
      step();
      auto id = pending.front();
      pending.pop_front();
      queued[id] = false;
      auto &block = blocks[id];
      Definitions incoming;
      if (id == graph.getEntry().getBlockID())
        incoming.insert(0);
      for (auto pred : block.native->preds())
        if (auto *p = pred.getReachableBlock()) {
          auto &before = blocks[p->getBlockID()];
          incoming.insert(before.out.begin(), before.out.end());
        }
      if (incoming.empty())
        continue;
      auto outgoing = incoming;
      for (auto i : block.usages)
        transfer(usages[i], outgoing);
      bool changed = !block.reachable || outgoing != block.out;
      block.reachable = true;
      cells -= block.in.size() + block.out.size();
      cells += incoming.size() + outgoing.size();
      if (cells > 1000000)
        throw BuildFailure(MatchCode::ResourceExhausted,
                           "variable flow state limit exceeded");
      block.in = std::move(incoming);
      block.out = std::move(outgoing);
      if (changed)
        for (auto next : block.native->succs())
          if (auto *successor = next.getReachableBlock()) {
            auto target = successor->getBlockID();
            if (!queued[target]) {
              pending.push_back(target);
              queued[target] = true;
            }
          }
    }
    bool changed;
    do {
      changed = false;
      for (auto &block : blocks) {
        if (!block.native || !block.reachable)
          continue;
        step();
        bool live = false;
        for (auto next : block.native->succs())
          if (auto *successor = next.getReachableBlock())
            live |= blocks[successor->getBlockID()].live_in;
        block.live_out = live;
        for (auto i = block.usages.rbegin(); i != block.usages.rend(); ++i) {
          auto kind = usages[*i].kind();
          if (writes(kind) || kind == Usage::DECLARE)
            live = false;
          if (reads(kind))
            live = true;
        }
        changed |= live != block.live_in;
        block.live_in = live;
      }
    } while (changed);
  }
  std::vector<unsigned> witness(std::size_t target) {
    // BFS over (block, uninitialized possibility) preserves statement order
    // while retaining a short CFG route, including loop-back paths.
    const unsigned root = graph.getEntry().getBlockID() * 2 + 1;
    std::vector<int> parent(blocks.size() * 2, -1);
    parent[root] = root;
    std::deque<unsigned> pending{root};
    while (!pending.empty()) {
      step();
      auto state = pending.front();
      pending.pop_front();
      auto id = state / 2;
      bool uninitialized = state % 2;
      for (auto i : blocks[id].usages) {
        if (i == target && uninitialized) {
          std::vector<unsigned> path;
          for (auto cursor = state;; cursor = parent[cursor]) {
            path.push_back(cursor / 2);
            if (cursor == root)
              break;
          }
          std::reverse(path.begin(), path.end());
          return path;
        }
        if (usages[i].kind() == Usage::DECLARE)
          uninitialized = true;
        else if (writes(usages[i].kind()))
          uninitialized = false;
      }
      for (auto next : blocks[id].native->succs())
        if (auto *successor = next.getReachableBlock()) {
          unsigned key = successor->getBlockID() * 2 + uninitialized;
          if (parent[key] < 0) {
            parent[key] = state;
            pending.push_back(key);
          }
        }
    }
    return {};
  }
  void publish() {
    std::uint64_t findings = 0;
    if (!unsupported.empty()) {
      pb::VariableFlowEvent event;
      auto *finding = event.mutable_finding();
      finding->set_kind(pb::VariableFlowFinding::UNSUPPORTED_EFFECT);
      finding->set_message(unsupported);
      emit(event);
      ++findings;
    }
    if (!ranges.issue.empty()) {
      pb::VariableFlowEvent event;
      auto *finding = event.mutable_finding();
      finding->set_kind(ranges.overflow
                            ? pb::VariableFlowFinding::POSSIBLE_OVERFLOW
                            : pb::VariableFlowFinding::UNSUPPORTED_EFFECT);
      finding->set_usage_id(ranges.issue_usage);
      finding->set_message(ranges.issue);
      emit(event);
      ++findings;
    }
    for (const auto &block : blocks) {
      if (!block.native)
        continue;
      auto state = block.in;
      std::vector<bool> live_after(block.usages.size());
      bool live = block.live_out;
      for (std::size_t j = block.usages.size(); j > 0; --j) {
        auto kind = usages[block.usages[j - 1]].kind();
        live_after[j - 1] = live;
        if (writes(kind) || kind == Usage::DECLARE)
          live = false;
        if (reads(kind))
          live = true;
      }
      for (std::size_t j = 0; j < block.usages.size(); ++j) {
        step();
        auto i = block.usages[j];
        const auto &usage = usages[i];
        pb::VariableFlowEvent event;
        auto *fact = event.mutable_fact();
        fact->set_usage_id(usage.id());
        fact->set_reachable(block.reachable);
        if (!unsupported.empty() || !block.reachable)
          fact->set_initialization(pb::VariableFlowFact::UNKNOWN);
        else {
          fact->set_initialization(
              state.contains(0)
                  ? (state.size() == 1
                         ? pb::VariableFlowFact::UNINITIALIZED
                         : pb::VariableFlowFact::MAYBE_INITIALIZED)
                  : pb::VariableFlowFact::INITIALIZED);
          if (reads(usage.kind()))
            for (auto definition : state)
              fact->add_reaching_assignments(definition);
          fact->set_live_after(live_after[j]);
          fact->set_dead_store(writes(usage.kind()) && !fact->live_after());
        }
        auto initialization = fact->initialization();
        bool dead = fact->dead_store();
        if (value_intervals) {
          fact->mutable_value_before()->CopyFrom(ranges.before[i]);
          fact->mutable_value_after()->CopyFrom(ranges.after[i]);
        }
        emit(event);
        if (block.reachable && unsupported.empty() && reads(usage.kind()) &&
            state.contains(0)) {
          event.Clear();
          auto *finding = event.mutable_finding();
          finding->set_usage_id(usage.id());
          finding->set_kind(
              initialization == pb::VariableFlowFact::UNINITIALIZED
                  ? pb::VariableFlowFinding::UNINITIALIZED_READ
                  : pb::VariableFlowFinding::POSSIBLY_UNINITIALIZED);
          finding->set_message(
              "read has an uninitialized route through the CFG");
          for (auto id : witness(i))
            finding->add_witness_blocks(id);
          emit(event);
          ++findings;
        }
        if (dead) {
          event.Clear();
          auto *finding = event.mutable_finding();
          finding->set_usage_id(usage.id());
          finding->set_kind(pb::VariableFlowFinding::DEAD_STORE);
          finding->set_message(
              "assigned value is never read before overwrite or exit");
          emit(event);
          ++findings;
        }
        transfer(usage, state);
      }
    }
    pb::VariableFlowEvent event;
    auto *done = event.mutable_completed();
    done->set_usage_count(usages.size());
    done->set_fact_count(usages.size());
    done->set_finding_count(findings);
    done->set_block_count(graph.size());
    done->set_iterations(iterations);
    done->set_is_complete(unsupported.empty() && ranges.issue.empty());
    emit(event);
  }
};
} // namespace
CfgResult
variable_flow(const pb::VariableFlowRequest &request,
              std::shared_ptr<const NativeBindingState> variable_state,
              std::shared_ptr<const NativeBindingState> function_state,
              const IMatchBackend::Checkpoint &checkpoint,
              const CfgLimits &limits, const ICfgBackend::VariableSink &sink) {
  try {
    if (!variable_state || !function_state || !variable_state->snapshot() ||
        variable_state->snapshot() != function_state->snapshot())
      return {MatchCode::InvalidArgument,
              "variable and function must share the same retained snapshot",
              {}};
    auto snapshot = variable_state->snapshot();
    std::lock_guard lane(snapshot->execution_mutex());
    const auto *variable =
        selected(*variable_state, request.variable()).get<clang::VarDecl>();
    const auto *function = selected(*function_state, request.function())
                               .get<clang::FunctionDecl>();
    if (!variable || !function || !variable->isLocalVarDecl() ||
        variable->isStaticLocal())
      return {MatchCode::InvalidArgument,
              "select a function definition and an automatic local variable",
              {}};
    if (!function->doesThisDeclarationHaveABody() ||
        function->isDependentContext())
      return {MatchCode::FailedPrecondition,
              "variable flow requires a concrete function definition",
              {}};
    if (variable->getParentFunctionOrMethod() != function)
      return {MatchCode::InvalidArgument,
              "variable does not belong to the selected function",
              {}};
    auto owner =
        std::dynamic_pointer_cast<const AstSnapshotOwner>(snapshot->owner);
    if (!owner || !owner->unit)
      return {MatchCode::Internal, "native snapshot unavailable", {}};
    auto &ast = owner->unit->getASTContext();
    if (checkpoint && !checkpoint())
      throw BuildFailure(MatchCode::Cancelled, "variable flow cancelled");
    clang::CFG::BuildOptions options;
    options.setAllAlwaysAdd();
    options.AddEHEdges = true;
    auto graph =
        clang::CFG::buildCFG(function, function->getBody(), &ast, options);
    if (!graph)
      return {MatchCode::FailedPrecondition,
              "Clang could not build variable CFG",
              {}};
    if (graph->size() >
        (request.has_max_blocks() ? request.max_blocks() : 10000))
      throw BuildFailure(MatchCode::ResourceExhausted,
                         "variable flow block limit exceeded");
    Analysis analysis{ast,
                      *variable,
                      *graph,
                      checkpoint,
                      sink,
                      request.has_max_events() ? request.max_events() : 10000,
                      request.has_max_iterations() ? request.max_iterations()
                                                   : 100000,
                      limits.max_bytes};
    auto type = variable->getType();
    analysis.value_intervals = request.value_domain() == pb::INTERVAL;
    if (!type->isIntegerType() || type.isVolatileQualified() ||
        variable->isExceptionVariable() ||
        variable->hasAttr<clang::CleanupAttr>())
      analysis.unsupported =
          "only direct non-volatile integer and Boolean "
          "locals without catch or cleanup effects are supported";
    pb::VariableFlowEvent event;
    auto *start = event.mutable_started();
    start->set_variable(variable->getNameAsString());
    start->set_function(function->getQualifiedNameAsString());
    start->set_snapshot_generation(snapshot->generation);
    start->set_declaration_id(static_cast<std::uint64_t>(variable->getID()));
    location(variable->getLocation(), ast, *start->mutable_declaration());
    start->set_entry_block(graph->getEntry().getBlockID());
    start->set_exit_block(graph->getExit().getBlockID());
    start->set_value_domain(request.value_domain());
    analysis.emit(event);
    analysis.classify();
    analysis.converge();
    if (analysis.value_intervals) {
      if (analysis.unsupported.empty())
        analysis.ranges = variable_ranges(
            ast, *variable, *graph, analysis.usages, analysis.usage_statements,
            [&analysis] { analysis.step(); });
      else {
        analysis.ranges.before.resize(analysis.usages.size());
        analysis.ranges.after.resize(analysis.usages.size());
        for (auto *values : {&analysis.ranges.before, &analysis.ranges.after})
          for (auto &value : *values)
            value.set_kind(pb::VariableValueRange::UNKNOWN);
      }
    }
    analysis.publish();
    return {};
  } catch (const BuildFailure &error) {
    return {error.code, error.what(), {}};
  } catch (const std::exception &error) {
    return {MatchCode::InvalidArgument, error.what(), {}};
  }
}
} // namespace ctk::clang_layer::control_flow
