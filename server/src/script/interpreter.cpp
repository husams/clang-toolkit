#include "interpreter.hpp"
#include "ctk/script/error.hpp"
#include "scoped_block.hpp"
#include <algorithm>
#include <unordered_set>
namespace ctk::script::detail {
using Code = ctk::clang_layer::MatchCode;
namespace {
Value scalar_value(ctk::analysis::v1::ScriptScalar scalar) {
  auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
  *wire->mutable_scalar() = std::move(scalar);
  return {wire, {}, {}};
}
Value integer_value(std::int64_t integer) {
  ctk::analysis::v1::ScriptScalar scalar;
  scalar.set_integer(integer);
  return scalar_value(std::move(scalar));
}
Value text_value(const std::string &text) {
  ctk::analysis::v1::ScriptScalar scalar;
  scalar.set_text(text);
  return scalar_value(std::move(scalar));
}
Value null_value() {
  auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
  wire->mutable_scalar();
  return {wire, {}, {}};
}
std::string field_text(const Value &value, const std::string &name) {
  if (!value.wire || !value.wire->has_scalar() ||
      value.wire->scalar().value_case() !=
          ctk::analysis::v1::ScriptScalar::kText)
    throw Error(Code::InvalidArgument, name + " must be text");
  return value.wire->scalar().text();
}
bool contains_live_tree(const ctk::analysis::v1::ScriptValue &value) {
  if (value.has_tree())
    return true;
  if (value.has_list())
    return std::any_of(value.list().values().begin(),
                       value.list().values().end(), contains_live_tree);
  if (value.has_object())
    for (const auto &[key, child] : value.object().fields()) {
      (void)key;
      if (contains_live_tree(child))
        return true;
    }
  return false;
}
std::size_t field_index(const Value &value) {
  if (!value.wire || !value.wire->has_scalar() ||
      value.wire->scalar().value_case() !=
          ctk::analysis::v1::ScriptScalar::kInteger ||
      value.wire->scalar().integer() < 0)
    throw Error(Code::InvalidArgument, "index must be a nonnegative integer");
  return static_cast<std::size_t>(value.wire->scalar().integer());
}
} // namespace
Interpreter::Interpreter(
    Environment *environment, Limits limits,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const std::map<std::string, ctk::analysis::v1::ScriptValue> &initial_values,
    ExportSink export_sink, bool collect_final)
    : environment_(environment), limits_(limits), checkpoint_(checkpoint),
      scopes_(1), export_sink_(std::move(export_sink)),
      collect_final_(collect_final) {
  for (const auto &[name, wire] : initial_values) {
    if (name.empty() || contains_live_tree(wire))
      throw Error(Code::InvalidArgument,
                  "initial script values must be named and detached");
    auto value = std::make_shared<ctk::analysis::v1::ScriptValue>(wire);
    Value imported{value, {}, {}};
    retain(imported);
    scopes_.front().emplace(name, std::move(imported));
  }
}
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
  auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
  if (value.wire->has_matches()) {
    if (index >= static_cast<std::size_t>(value.wire->matches().rows_size()))
      throw Error(Code::InvalidArgument,
                  "row requires matched rows and an in-range index");
    *wire->mutable_matches()->add_rows() =
        value.wire->matches().rows(static_cast<int>(index));
  } else if (value.wire->has_list()) {
    if (index >= static_cast<std::size_t>(value.wire->list().values_size()))
      throw Error(Code::NotFound, "script list index out of range");
    wire->CopyFrom(value.wire->list().values(static_cast<int>(index)));
  } else {
    throw Error(Code::InvalidArgument,
                "row requires matched rows or a list and an in-range index");
  }
  Value result{wire, value.bindings, {}};
  if (value.native_rows)
    result.native_rows = std::make_shared<const std::vector<std::size_t>>(
        std::vector<std::size_t>{value.native_rows->at(index)});
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
  if (expression.kind == Expression::Kind::List ||
      expression.kind == Expression::Kind::Object) {
    auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
    Value result{wire, {}, {}};
    if (expression.kind == Expression::Kind::List) {
      auto *values = wire->mutable_list();
      for (const auto &element : expression.elements) {
        tick();
        *values->add_values() = *evaluate(*element).wire;
      }
    } else {
      auto *fields = wire->mutable_object()->mutable_fields();
      for (std::size_t i = 0; i < expression.elements.size(); ++i) {
        tick();
        auto value = evaluate(*expression.elements[i]);
        (*fields)[expression.keys.at(i)].CopyFrom(*value.wire);
      }
    }
    retain(result);
    return result;
  }
  if (expression.kind == Expression::Kind::Member ||
      expression.kind == Expression::Kind::Index) {
    auto base = evaluate(*expression.source);
    Value selected;
    if (expression.kind == Expression::Kind::Member) {
      if (base.wire->has_object()) {
        auto found = base.wire->object().fields().find(expression.name);
        if (found == base.wire->object().fields().end())
          throw Error(Code::NotFound,
                      "script object field not found: " + expression.name);
        selected.wire =
            std::make_shared<ctk::analysis::v1::ScriptValue>(found->second);
      } else if (base.wire->has_files() && expression.name == "inputs") {
        auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
        wire->mutable_files()->CopyFrom(base.wire->files());
        selected.wire = std::move(wire);
      } else if (base.wire->has_files() && expression.name == "paths") {
        auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
        auto *values = wire->mutable_list();
        for (const auto &input : base.wire->files().inputs())
          *values->add_values()->mutable_scalar()->mutable_text() =
              input.file_path();
        selected.wire = std::move(wire);
      } else if (base.wire->has_files() && expression.name == "length") {
        selected = integer_value(base.wire->files().inputs_size());
      } else {
        throw Error(Code::InvalidArgument,
                    "script value has no member: " + expression.name);
      }
    } else {
      auto index = evaluate(*expression.elements.front());
      const auto offset = field_index(index);
      if (base.wire->has_list()) {
        if (offset >= static_cast<std::size_t>(base.wire->list().values_size()))
          throw Error(Code::NotFound, "script list index out of range");
        selected.wire = std::make_shared<ctk::analysis::v1::ScriptValue>(
            base.wire->list().values(static_cast<int>(offset)));
      } else if (base.wire->has_files()) {
        if (offset >=
            static_cast<std::size_t>(base.wire->files().inputs_size()))
          throw Error(Code::NotFound, "file manifest index out of range");
        auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
        *wire->mutable_files()->add_inputs() =
            base.wire->files().inputs(static_cast<int>(offset));
        selected.wire = std::move(wire);
      } else {
        throw Error(Code::InvalidArgument, "script value cannot be indexed");
      }
    }
    retain(selected);
    return selected;
  }
  tick();
  if (expression.kind == Expression::Kind::Scoped)
    return scoped(*expression.block);
  if (expression.kind == Expression::Kind::Files) {
    if (!environment_)
      throw Error(Code::FailedPrecondition,
                  "file discovery requires a native environment");
    auto pattern = evaluate(*expression.source);
    auto value = environment_->files(field_text(pattern, "files pattern"));
    retain(value);
    return value;
  }
  if (expression.kind == Expression::Kind::Group)
    return evaluate(*expression.source);
  if (expression.kind == Expression::Kind::Foreach) {
    auto source = evaluate(*expression.source);
    std::vector<Value> items;
    if (source.wire->has_list()) {
      items.reserve(source.wire->list().values_size());
      for (const auto &wire : source.wire->list().values())
        items.push_back(
            {std::make_shared<ctk::analysis::v1::ScriptValue>(wire), {}, {}});
    } else if (source.wire->has_files()) {
      items.reserve(source.wire->files().inputs_size());
      for (const auto &input : source.wire->files().inputs()) {
        auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
        *wire->mutable_files()->add_inputs() = input;
        items.push_back({wire, {}, {}});
      }
    } else if (source.wire->has_matches()) {
      for (int i = 0; i < source.wire->matches().rows_size(); ++i)
        items.push_back(row(source, static_cast<std::size_t>(i)));
    } else {
      throw Error(
          Code::InvalidArgument,
          "foreach expression requires a list, files or native matches");
    }
    if (items.size() > 10000)
      throw Error(Code::ResourceExhausted, "foreach item limit exceeded");
    auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
    auto *output = wire->mutable_list();
    for (const auto &item : items) {
      tick();
      const auto depth = scopes_.size();
      scopes_.emplace_back();
      scopes_.back().emplace(expression.iteration_name, item);
      try {
        auto final = statements(expression.batch_body->statements);
        *output->add_values() = *final.wire;
        scopes_.resize(depth);
      } catch (...) {
        scopes_.resize(depth);
        throw;
      }
    }
    Value result{wire, {}, {}};
    retain(result);
    return result;
  }
  if (expression.kind == Expression::Kind::Batch) {
    if (!environment_)
      throw Error(Code::FailedPrecondition,
                  "batch execution requires a native environment");
    auto manifest = evaluate(*expression.source);
    if (!manifest.wire || !manifest.wire->has_files())
      throw Error(Code::InvalidArgument, "batch requires a file manifest");
    const auto total =
        static_cast<std::size_t>(manifest.wire->files().inputs_size());
    if ((!expression.count && (expression.option != "count" || total != 0)) ||
        (expression.option == "count" && expression.count &&
         (!total || expression.count > total)))
      throw Error(Code::InvalidArgument, "batch size/count is out of range");
    const auto groups = expression.option == "count"
                            ? std::min(expression.count, total)
                            : (total + expression.count - 1) / expression.count;
    if (expression.jobs > limits_.max_steps)
      throw Error(Code::InvalidArgument, "batch jobs exceed script limits");
    auto report = std::make_shared<ctk::analysis::v1::ScriptValue>();
    auto *fields = report->mutable_object()->mutable_fields();
    auto put_text = [&](const std::string &key, const std::string &text) {
      auto &value = (*fields)[key];
      value.mutable_scalar()->set_text(text);
    };
    auto put_integer = [&](const std::string &key, std::int64_t number) {
      auto &value = (*fields)[key];
      value.mutable_scalar()->set_integer(number);
    };
    auto put_boolean = [&](const std::string &key, bool enabled) {
      auto &value = (*fields)[key];
      value.mutable_scalar()->set_boolean(enabled);
    };
    auto *results = (*fields)["results"].mutable_list();
    auto *indices = (*fields)["result_group_indices"].mutable_list();
    auto *errors = (*fields)["group_errors"].mutable_list();
    std::size_t failed = 0;
    std::size_t completed = 0;
    std::size_t begin = 0;
    for (std::size_t group_index = 0; group_index < groups; ++group_index) {
      tick();
      const std::size_t group_size =
          expression.option == "count"
              ? total / groups + (group_index < total % groups ? 1 : 0)
              : std::min(expression.count, total - begin);
      auto group = std::make_shared<ctk::analysis::v1::ScriptValue>();
      auto *group_fields = group->mutable_object()->mutable_fields();
      (*group_fields)["index"].mutable_scalar()->set_integer(group_index + 1);
      auto *group_inputs = (*group_fields)["inputs"].mutable_files();
      auto *paths = (*group_fields)["paths"].mutable_list();
      for (std::size_t j = 0; j < group_size; ++j) {
        *group_inputs->add_inputs() =
            manifest.wire->files().inputs(static_cast<int>(begin + j));
        paths->add_values()->mutable_scalar()->set_text(
            manifest.wire->files()
                .inputs(static_cast<int>(begin + j))
                .file_path());
      }
      (*group_fields)["length"].mutable_scalar()->set_integer(group_size);
      const auto group_value = Value{group, {}, {}};
      bool success = false;
      Value output = null_value();
      bool began = false;
      const auto scope_depth = scopes_.size();
      try {
        environment_->begin_batch_group(group_value, group_index + 1,
                                        expression.jobs,
                                        expression.memory_bytes);
        began = true;
        scopes_.emplace_back();
        scopes_.back().emplace(expression.iteration_name, group_value);
        output = statements(expression.batch_body->statements);
        scopes_.resize(scope_depth);
        auto detached =
            std::make_shared<ctk::analysis::v1::ScriptValue>(*output.wire);
        output = {};
        output.wire = std::move(detached);
        success = true;
      } catch (const Error &error) {
        scopes_.resize(scope_depth);
        if (began)
          environment_->end_batch_group(false);
        if (error.code == Code::Cancelled)
          throw;
        ++failed;
        if (errors->values_size() < 8) {
          auto *entry =
              errors->add_values()->mutable_object()->mutable_fields();
          (*entry)["index"].mutable_scalar()->set_integer(group_index + 1);
          (*entry)["message"].mutable_scalar()->set_text(error.what());
        }
        if (!expression.continue_on_error)
          break;
      } catch (const std::exception &error) {
        scopes_.resize(scope_depth);
        if (began)
          environment_->end_batch_group(false);
        ++failed;
        if (errors->values_size() < 8) {
          auto *entry =
              errors->add_values()->mutable_object()->mutable_fields();
          (*entry)["index"].mutable_scalar()->set_integer(group_index + 1);
          (*entry)["message"].mutable_scalar()->set_text(error.what());
        }
        if (!expression.continue_on_error)
          break;
      }
      if (success) {
        environment_->end_batch_group(true);
        // Collection stores wire data only; native continuation state stays in
        // the group and is released before the next group begins.
        *results->add_values() = *output.wire;
        indices->add_values()->mutable_scalar()->set_integer(group_index + 1);
        ++completed;
        // Charge detached report growth before admitting another group. The
        // report intentionally contains no native binding state.
        retain({report, {}, {}});
      }
      begin += group_size;
    }
    put_text("status", failed ? "failed" : "completed");
    put_boolean("progress", expression.progress);
    put_integer("completed_groups", completed);
    put_integer("failed_groups", failed);
    put_integer("skipped_groups", groups - completed - failed);
    auto &complete = (*fields)["results_complete"];
    complete.mutable_scalar()->set_boolean(failed == 0 && completed == groups);
    retain({report, {}, {}});
    return {report, {}, {}};
  }
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
      if (expression.target) {
        const auto &target_expression = *expression.target;
        if (target_expression.kind == Expression::Kind::Member &&
            target_expression.name == "paths" && target_expression.source) {
          auto base = evaluate(*target_expression.source);
          if (base.wire && base.wire->has_object()) {
            const auto inputs = base.wire->object().fields().find("inputs");
            if (inputs != base.wire->object().fields().end() &&
                inputs->second.has_files()) {
              target = Value{std::make_shared<ctk::analysis::v1::ScriptValue>(
                                 inputs->second),
                             {},
                             {}};
            }
          }
        }
        if (!target)
          target = evaluate(*expression.target);
      } else if (!default_trees_.empty()) {
        target = default_trees_.back();
      }
      result = environment_->match(expression.name, target ? &*target : nullptr,
                                   expression.binding, {});
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
    else if (wire.has_list())
      count = wire.list().values_size();
    else if (wire.has_files())
      count = wire.files().inputs_size();
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
  } else if (expression.name == "flatten") {
    if (arguments.size() != 1 || !options.empty() ||
        !arguments.front().wire->has_list())
      throw Error(Code::InvalidArgument, "flatten requires one list");
    auto wire = std::make_shared<ctk::analysis::v1::ScriptValue>();
    auto *output = wire->mutable_list();
    std::function<void(const ctk::analysis::v1::ScriptValue &)> append_flat;
    append_flat = [&](const ctk::analysis::v1::ScriptValue &child) {
      if (child.has_list()) {
        for (const auto &nested : child.list().values())
          append_flat(nested);
      } else if (child.has_matches()) {
        for (const auto &row : child.matches().rows()) {
          if (output->values_size() >= 10000)
            throw Error(Code::ResourceExhausted,
                        "flatten result item limit exceeded");
          *output->add_values()->mutable_matches()->add_rows() = row;
        }
      } else if (child.has_traversal()) {
        if (child.traversal().nodes_size() > 10000 - output->values_size())
          throw Error(Code::ResourceExhausted,
                      "flatten result item limit exceeded");
        for (const auto &node : child.traversal().nodes())
          *output->add_values()->mutable_traversal()->add_nodes() = node;
      } else if (child.has_call_graph()) {
        if (child.call_graph().nodes_size() > 10000 - output->values_size())
          throw Error(Code::ResourceExhausted,
                      "flatten result item limit exceeded");
        for (const auto &node : child.call_graph().nodes())
          *output->add_values()->mutable_call_graph()->add_nodes() = node;
      } else if (child.has_cfg()) {
        if (child.cfg().graphs_size() > 10000 - output->values_size())
          throw Error(Code::ResourceExhausted,
                      "flatten result item limit exceeded");
        for (const auto &graph : child.cfg().graphs())
          *output->add_values()->mutable_cfg()->add_graphs() = graph;
      } else if (child.has_scalar() || child.has_object() ||
                 child.has_files() || child.has_tree()) {
        if (output->values_size() >= 10000)
          throw Error(Code::ResourceExhausted,
                      "flatten result item limit exceeded");
        *output->add_values() = child;
      } else {
        throw Error(Code::InvalidArgument,
                    "flatten requires nested list or analysis collections");
      }
    };
    for (const auto &child : arguments.front().wire->list().values())
      append_flat(child);
    result.wire = std::move(wire);
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
std::string Interpreter::interpolate(const std::string &text) const {
  std::string result = text;
  std::size_t offset = 0;
  while ((offset = result.find("${", offset)) != std::string::npos) {
    const auto end = result.find('}', offset + 2);
    if (end == std::string::npos)
      throw Error(Code::InvalidArgument,
                  "unterminated script string interpolation");
    const auto token = result.substr(offset + 2, end - offset - 2);
    const auto dot = token.find('.');
    const auto variable = token.substr(0, dot);
    const Value *value = nullptr;
    for (auto scope = scopes_.rbegin(); scope != scopes_.rend(); ++scope) {
      const auto found = scope->find(variable);
      if (found != scope->end()) {
        value = &found->second;
        break;
      }
    }
    if (!value)
      throw Error(Code::InvalidArgument,
                  "undefined interpolation variable: " + variable);
    std::size_t field_start = dot == std::string::npos ? token.size() : dot + 1;
    while (field_start < token.size()) {
      const auto next = token.find('.', field_start);
      const auto field = token.substr(field_start, next == std::string::npos
                                                       ? std::string::npos
                                                       : next - field_start);
      if (!value->wire || !value->wire->has_object())
        throw Error(Code::InvalidArgument,
                    "interpolation path must reference an object field");
      const auto found = value->wire->object().fields().find(field);
      if (found == value->wire->object().fields().end())
        throw Error(Code::NotFound, "interpolation field not found: " + field);
      value = nullptr;
      // Keep one stable owner while walking nested message values.
      auto shared =
          std::make_shared<ctk::analysis::v1::ScriptValue>(found->second);
      const bool last = next == std::string::npos;
      if (last) {
        const auto &scalar = shared->scalar();
        std::string replacement;
        switch (scalar.value_case()) {
        case ctk::analysis::v1::ScriptScalar::kText:
          replacement = scalar.text();
          break;
        case ctk::analysis::v1::ScriptScalar::kInteger:
          replacement = std::to_string(scalar.integer());
          break;
        case ctk::analysis::v1::ScriptScalar::kNumber:
          replacement = std::to_string(scalar.number());
          break;
        case ctk::analysis::v1::ScriptScalar::kBoolean:
          replacement = scalar.boolean() ? "true" : "false";
          break;
        default:
          throw Error(Code::InvalidArgument,
                      "interpolation value must be scalar");
        }
        result.replace(offset, end - offset + 1, replacement);
        offset += replacement.size();
        break;
      }
      // Nested interpolation paths are not needed by batch destinations yet.
      throw Error(Code::InvalidArgument,
                  "nested interpolation paths are unsupported");
    }
    if (dot == std::string::npos)
      throw Error(Code::InvalidArgument,
                  "interpolation must name an object field");
  }
  return result;
}
Value Interpreter::statements(const std::vector<Statement> &body) {
  Value last = null_value();
  for (const auto &statement : body) {
    tick();
    auto value = evaluate(*statement.expression);
    if (statement.kind == Statement::Kind::Assignment) {
      if (scopes_.back().contains(statement.name))
        throw Error(Code::InvalidArgument,
                    "duplicate script variable: " + statement.name);
      scopes_.back().emplace(statement.name, std::move(value));
      last = scopes_.back().at(statement.name);
    } else if (statement.kind == Statement::Kind::Emission) {
      auto *emission = response_.add_emissions();
      if (statement.expression->kind == Expression::Kind::Reference)
        emission->set_name(statement.expression->name);
      *emission->mutable_value() = *value.wire;
      if (response_.ByteSizeLong() > limits_.max_response_bytes)
        throw Error(Code::ResourceExhausted,
                    "script response byte limit exceeded");
      retain(value);
      last = value;
    } else if (statement.kind == Statement::Kind::Save) {
      auto destination = evaluate(*statement.destination);
      const auto path =
          interpolate(field_text(destination, "save destination"));
      if (export_sink_) {
        auto [code, message] =
            export_sink_(path, *value.wire, statement.option);
        if (code != Code::Ok)
          throw Error(code, message.empty() ? "script export failed" : message);
      } else if (environment_) {
        (void)environment_->save(path, value, statement.option);
      } else {
        throw Error(Code::FailedPrecondition,
                    "script export requires a native environment");
      }
      last = null_value();
    } else if (statement.kind == Statement::Kind::Value) {
      last = value;
    } else {
      if (!value.wire ||
          (!value.wire->has_matches() && !value.wire->has_list()))
        throw Error(Code::InvalidArgument,
                    "foreach requires a list or matched rows");
      const auto count = value.wire->has_matches()
                            ? static_cast<std::size_t>(
                                  value.wire->matches().rows_size())
                            : static_cast<std::size_t>(
                                  value.wire->list().values_size());
      if (count > 10000)
        throw Error(Code::ResourceExhausted, "foreach item limit exceeded");
      auto collected = std::make_shared<ctk::analysis::v1::ScriptValue>();
      auto *items = collected->mutable_list();
      for (std::size_t index = 0; index < count; ++index) {
        tick();
        scopes_.emplace_back();
        try {
          scopes_.back().emplace(statement.name, row(value, index));
          *items->add_values() = *statements(statement.body).wire;
        } catch (...) {
          scopes_.pop_back();
          throw;
        }
        scopes_.pop_back();
      }
      last = {collected, {}, {}};
      retain(last);
    }
  }
  return last;
}
ctk::analysis::v1::ScriptResponse Interpreter::run(const Program &program) {
  final_value_ = statements(program.statements);
  if (collect_final_ && final_value_.wire) {
    auto *emission = response_.add_emissions();
    emission->set_name("__final__");
    *emission->mutable_value() = *final_value_.wire;
  }
  if (!checkpoint_())
    throw Error(Code::Cancelled, "script cancelled before publication");
  if (response_.ByteSizeLong() > limits_.max_response_bytes)
    throw Error(Code::ResourceExhausted, "script response byte limit exceeded");
  return std::move(response_);
}
} // namespace ctk::script::detail
