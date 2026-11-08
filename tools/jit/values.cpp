#include "values.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <utility>

#include <clang/AST/ASTTypeTraits.h>
#include <clang/AST/DeclCXX.h>
#include <clang/AST/Stmt.h>
#include <llvm/ADT/SmallPtrSet.h>
#include <llvm/ExecutionEngine/Orc/LLJIT.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/MathExtras.h>

namespace ctk::jit {

const Value* Values::hold(Value value) { return &temporaries.emplace_back(std::move(value)); }

const Value* Values::fail(const llvm::Twine& message) {
  error = message.str();
  return nullptr;
}

Value* Values::lookup(llvm::StringRef name) {
  for (auto it = scopes.rbegin(); it != scopes.rend(); ++it) {
    if (auto entry = it->bindings.find(name); entry != it->bindings.end()) {
      return &entry->second;
    }
  }
  const auto entry = globals.find(name);
  return entry == globals.end() ? nullptr : &entry->second;
}

Bindings& Values::local() { return scopes.empty() ? globals : scopes.back().bindings; }

void Values::push() { scopes.emplace_back(); }

void Values::pop() { scopes.pop_back(); }

bool Values::tick() {
  if (++steps > 1000000) {
    fatal = true;
    fail("execution step limit exceeded");
    return false;
  }
  return true;
}

namespace {

constexpr std::size_t max_items = 10000;

template <typename T> const T* as(const Value& value) { return std::get_if<T>(&value.data); }

template <typename T> T* object(const Value& value) {
  const auto* handle = as<std::shared_ptr<T>>(value);
  return handle ? handle->get() : nullptr;
}

Value list(std::vector<Value> items = {}, bool tuple = false) {
  return {std::make_shared<Sequence>(Sequence{std::move(items), tuple})};
}

Value record() { return {std::make_shared<Record>()}; }

template <typename T> Value related(const NativeNode& original, const T& node) {
  return {std::make_shared<NativeNode>(NativeNode{
      original.ast, std::make_shared<clang::DynTypedNode>(clang::DynTypedNode::create(node))})};
}

std::optional<Value> node_property(const NativeNode& native, llvm::StringRef key) {
  const auto& node = *native.node;
  if (key == "kind")
    return Value{node.getNodeKind().asStringRef().str()};
  if (const auto* decl = node.get<clang::NamedDecl>()) {
    if (key == "decl_name" || key == "name")
      return Value{decl->getNameAsString()};
    if (key == "qualified_name")
      return Value{decl->getQualifiedNameAsString()};
  }
  if (const auto* decl = node.get<clang::Decl>()) {
    if (key == "is_implicit")
      return Value{decl->isImplicit()};
  }
  if (const auto* decl = node.get<clang::ValueDecl>()) {
    if (key == "type") {
      return related(native, decl->getType());
    }
  }
  if (const auto* function = node.get<clang::FunctionDecl>()) {
    if (key == "is_definition")
      return Value{function->isThisDeclarationADefinition()};
    if (key == "return_type") {
      return related(native, function->getReturnType());
    }
    if (key == "parameters") {
      auto result = list();
      for (const auto* param : function->parameters()) {
        object<Sequence>(result)->items.push_back(related(native, *param));
      }
      return result;
    }
  }
  if (const auto* type = node.get<clang::QualType>()) {
    if (key == "spelling" || key == "name")
      return Value{type->getAsString()};
  }
  return std::nullopt;
}

void format(llvm::raw_ostream& out, const Value& value, bool quote) {
  if (const auto* string = as<std::string>(value)) {
    if (quote) {
      out << llvm::json::Value(*string);
    } else {
      out << *string;
    }
  } else if (const auto* flag = as<bool>(value)) {
    out << (*flag ? "true" : "false");
  } else if (const auto* integer = as<std::int64_t>(value)) {
    out << *integer;
  } else if (const auto* floating = as<double>(value)) {
    out << llvm::json::Value(*floating);
  } else if (const auto* sequence = object<Sequence>(value)) {
    out << (sequence->tuple ? '(' : '[');
    llvm::StringRef separator;
    for (const auto& item : sequence->items) {
      out << separator;
      format(out, item, true);
      separator = ",";
    }
    if (sequence->tuple && sequence->items.size() == 1) {
      out << ',';
    }
    out << (sequence->tuple ? ')' : ']');
  } else if (const auto* data = object<Record>(value)) {
    out << '{';
    llvm::StringRef separator;
    for (const auto& key : data->keys) {
      out << separator << llvm::json::Value(key) << ':';
      format(out, data->fields.find(key)->second, true);
      separator = ",";
    }
    out << '}';
  } else if (const auto* node = object<NativeNode>(value)) {
    const auto name = node_property(*node, "decl_name");
    out << node->node->getNodeKind().asStringRef();
    if (name)
      out << '(' << *as<std::string>(*name) << ')';
  } else if (const auto* matcher = as<MatcherValue>(value)) {
    out << matcher->text;
  } else if (const auto* runnable = object<Runnable>(value)) {
    out << runnable->name;
  } else {
    out << "null";
  }
}

std::size_t rune_size(unsigned char lead) {
  if (lead < 0x80)
    return 1;
  if (lead < 0xe0)
    return 2;
  if (lead < 0xf0)
    return 3;
  return 4;
}

std::size_t string_length(llvm::StringRef value) {
  return llvm::count_if(value, [](unsigned char byte) { return (byte & 0xc0) != 0x80; });
}

std::optional<std::size_t> length(const Value& value) {
  if (const auto* string = as<std::string>(value))
    return string_length(*string);
  if (const auto* sequence = object<Sequence>(value))
    return sequence->items.size();
  if (const auto* data = object<Record>(value))
    return data->keys.size();
  return std::nullopt;
}

bool scalar(const Value& value) { return value.data.index() < 5; }

std::optional<double> number(const Value& value) {
  if (auto* integer = as<std::int64_t>(value))
    return static_cast<double>(*integer);
  if (auto* floating = as<double>(value))
    return *floating;
  return std::nullopt;
}

bool lossless(std::int64_t integer, double converted) {
  // The upper bound rounds up to 2^63. Check it before converting back.
  return converted < 0x1p63 && static_cast<std::int64_t>(converted) == integer;
}

const Value* finite(Values& runtime, double value) {
  return std::isfinite(value) ? runtime.hold({value})
                              : runtime.fail("non-finite floating-point result");
}

template <typename T> bool compare(llvm::StringRef op, const T& left, const T& right) {
  if (op == "<")
    return left < right;
  if (op == "<=")
    return left <= right;
  if (op == ">")
    return left > right;
  if (op == ">=")
    return left >= right;
  return op == "==" ? left == right : left != right;
}

const Value* binary(Values& runtime, llvm::StringRef op, const Value& left, const Value& right) {
  const auto* lhs_string = as<std::string>(left);
  const auto* rhs_string = as<std::string>(right);
  if (lhs_string && rhs_string) {
    if (op == "+")
      return runtime.hold({*lhs_string + *rhs_string});
    if (op == "==" || op == "!=" || op == "<" || op == "<=" || op == ">" || op == ">=") {
      return runtime.hold({compare(op, *lhs_string, *rhs_string)});
    }
  }
  const auto lhs = number(left);
  const auto rhs = number(right);
  if (!lhs || !rhs) {
    if (op == "==" || op == "!=") {
      if (as<bool>(left) || as<bool>(right) || std::holds_alternative<std::monostate>(left.data) ||
          std::holds_alternative<std::monostate>(right.data)) {
        const auto* l = as<bool>(left);
        const auto* r = as<bool>(right);
        const bool equal = l && r ? *l == *r : left.data.index() == right.data.index();
        return runtime.hold({op == "==" ? equal : !equal});
      }
      return runtime.fail("equality supports scalar values only");
    }
    return runtime.fail("numeric operands required");
  }

  const auto* l = as<std::int64_t>(left);
  const auto* r = as<std::int64_t>(right);
  const bool comparison =
      op == "==" || op == "!=" || op == "<" || op == "<=" || op == ">" || op == ">=";
  if (l && r && op != "/") {
    if (comparison)
      return runtime.hold({compare(op, *l, *r)});
    std::int64_t result = 0;
    bool overflow = false;
    if (op == "+")
      overflow = llvm::AddOverflow(*l, *r, result);
    else if (op == "-")
      overflow = llvm::SubOverflow(*l, *r, result);
    else if (op == "*")
      overflow = llvm::MulOverflow(*l, *r, result);
    else if (op == "%") {
      if (*r == 0)
        return runtime.fail("remainder by zero");
      result = *r == -1 ? 0 : *l % *r;
    } else {
      return runtime.fail(llvm::Twine("unknown binary operator ") + op);
    }
    return overflow ? runtime.fail("signed 64-bit integer overflow") : runtime.hold({result});
  }
  if ((!l && r && !lossless(*r, *rhs)) || (l && !r && !lossless(*l, *lhs))) {
    return runtime.fail("integer-to-float conversion is not lossless");
  }
  if (comparison)
    return runtime.hold({compare(op, *lhs, *rhs)});
  if (op == "+")
    return finite(runtime, *lhs + *rhs);
  if (op == "-")
    return finite(runtime, *lhs - *rhs);
  if (op == "*")
    return finite(runtime, *lhs * *rhs);
  if (op == "/") {
    if (*rhs == 0.0)
      return runtime.fail("division by zero");
    if (l && r)
      return finite(runtime, static_cast<long double>(*l) / *r);
    return finite(runtime, *lhs / *rhs);
  }
  return runtime.fail("remainder requires integer operands");
}

bool references(const Value& value, const Sequence* sequence, const Record* data,
                llvm::SmallPtrSetImpl<const void*>& visited) {
  if (const auto* items = object<Sequence>(value)) {
    return items == sequence ||
           (visited.insert(items).second && llvm::any_of(items->items, [&](const Value& item) {
              return references(item, sequence, data, visited);
            }));
  }
  if (const auto* fields = object<Record>(value)) {
    return fields == data ||
           (visited.insert(fields).second && llvm::any_of(fields->fields, [&](const auto& field) {
              return references(field.second, sequence, data, visited);
            }));
  }
  if (const auto* function = object<Runnable>(value); function && visited.insert(function).second) {
    return llvm::any_of(function->captured, [&](const Scope& scope) {
      return llvm::any_of(scope.bindings, [&](const auto& binding) {
        return references(binding.second, sequence, data, visited);
      });
    });
  }
  return false;
}

bool references(const Value& value, const Sequence* sequence, const Record* data) {
  llvm::SmallPtrSet<const void*, 16> visited;
  return references(value, sequence, data, visited);
}

extern "C" const Value* ctk_jit_value_literal_v1(Values* runtime, const char* text,
                                                 std::int64_t length, std::int32_t type) {
  llvm::StringRef input(text, length);
  switch (type) {
  case 0:
    return runtime->hold({});
  case 1:
    return runtime->hold({input == "true"});
  case 2: {
    std::int64_t integer;
    if (!input.getAsInteger(10, integer))
      return runtime->hold({integer});
    break;
  }
  case 3: {
    double floating;
    if (!input.getAsDouble(floating))
      return finite(*runtime, floating);
    break;
  }
  case 4:
    return runtime->hold({input.str()});
  }
  return runtime->fail("invalid literal");
}

extern "C" const Value* ctk_jit_value_lookup_v1(Values* runtime, const char* name) {
  if (const auto* value = runtime->lookup(name))
    return runtime->hold(*value);
  return runtime->fail(llvm::Twine("undefined binding '") + name + "'");
}

extern "C" void ctk_jit_value_define_v1(Values* runtime, const char* name, const Value* value,
                                        std::int64_t ordinal) {
  runtime->local().insert_or_assign(name, *value);
  if (!runtime->scopes.empty()) {
    auto& ordinals = runtime->scopes.back().ordinals;
    if (ordinal < 0)
      ordinals.erase(name);
    else
      ordinals.insert_or_assign(name, ordinal);
  }
}

extern "C" const Value* ctk_jit_value_assign_v1(Values* runtime, const char* name,
                                                const Value* value) {
  if (auto* binding = runtime->lookup(name)) {
    *binding = *value;
    return value;
  }
  return runtime->fail(llvm::Twine("cannot assign undefined binding '") + name + "'");
}

extern "C" const Value* ctk_jit_value_binary_v1(Values* runtime, const char* op, const Value* left,
                                                const Value* right) {
  return binary(*runtime, op, *left, *right);
}

extern "C" const Value* ctk_jit_value_unary_v1(Values* runtime, const char* op,
                                               const Value* value) {
  if (llvm::StringRef(op) == "not") {
    const auto* flag = as<bool>(*value);
    return flag ? runtime->hold({!*flag}) : runtime->fail("condition requires bool");
  }
  if (as<std::int64_t>(*value) || as<double>(*value)) {
    if (*op == '+')
      return value;
    if (const auto* floating = as<double>(*value))
      return finite(*runtime, -*floating);
    return binary(*runtime, "-", Value{std::int64_t{0}}, *value);
  }
  return runtime->fail("invalid unary operation");
}

extern "C" std::int32_t ctk_jit_value_truth_v1(Values* runtime, const Value* value) {
  if (const auto* flag = as<bool>(*value))
    return *flag;
  runtime->fail("condition requires bool");
  return -1;
}

extern "C" const Value* ctk_jit_value_new_v1(Values* runtime, std::int32_t kind) {
  return runtime->hold(kind == 2 ? record() : list({}, kind == 1));
}

extern "C" const Value* ctk_jit_value_add_v1(Values* runtime, const Value* collection,
                                             const Value* key, const Value* item) {
  if (auto* sequence = object<Sequence>(*collection)) {
    if (sequence->items.size() >= max_items)
      return runtime->fail("list exceeds item limit");
    if (references(*item, sequence, nullptr))
      return runtime->fail("cyclic collection");
    sequence->items.push_back(*item);
  } else if (auto* data = object<Record>(*collection)) {
    const auto* name = key ? as<std::string>(*key) : nullptr;
    if (!name)
      return runtime->fail("record key must be a string");
    if (data->keys.size() >= max_items && !data->fields.contains(*name)) {
      return runtime->fail("dictionary exceeds item limit");
    }
    if (references(*item, nullptr, data))
      return runtime->fail("cyclic collection");
    data->set(*name, *item);
  }
  return collection;
}

extern "C" const Value* ctk_jit_value_get_v1(Values* runtime, const Value* value, const char* key,
                                             const char* reference) {
  const llvm::StringRef property(key);
  if (reference && (property == "index" || property == "value")) {
    for (auto it = runtime->scopes.rbegin(); it != runtime->scopes.rend(); ++it) {
      if (const auto ordinal = it->ordinals.find(reference); ordinal != it->ordinals.end()) {
        return property == "index" ? runtime->hold({ordinal->second}) : value;
      }
      if (it->bindings.contains(reference))
        break;
    }
  }
  if (const auto* data = object<Record>(*value)) {
    if (const auto found = data->fields.find(key); found != data->fields.end()) {
      return runtime->hold(found->second);
    }
    return runtime->fail(llvm::Twine("no record field named '") + key + "'");
  }
  if (const auto* node = object<NativeNode>(*value)) {
    if (auto field = node_property(*node, property))
      return runtime->hold(std::move(*field));
  }
  if (const auto size = length(*value)) {
    if (property == "length")
      return runtime->hold({static_cast<std::int64_t>(*size)});
    if (property == "isEmpty")
      return runtime->hold({*size == 0});
  }
  return runtime->fail(llvm::Twine("no property named '") + key + "'");
}

std::optional<std::size_t> position(const Value& key, std::size_t size) {
  const auto* integer = as<std::int64_t>(key);
  if (!integer)
    return std::nullopt;
  auto index = *integer;
  if (index < 0)
    index += static_cast<std::int64_t>(size);
  if (index < 0 || static_cast<std::uint64_t>(index) >= size)
    return std::nullopt;
  return static_cast<std::size_t>(index);
}

extern "C" const Value* ctk_jit_value_index_v1(Values* runtime, const Value* value,
                                               const Value* key) {
  if (const auto* data = object<Record>(*value)) {
    const auto* name = as<std::string>(*key);
    if (!name)
      return runtime->fail("record index must be a string");
    const auto found = data->fields.find(*name);
    if (found != data->fields.end())
      return runtime->hold(found->second);
    return runtime->fail(llvm::Twine("no record field named '") + *name + "'");
  }
  const auto size = length(*value);
  if (!size)
    return runtime->fail("value is not indexable");
  if (!as<std::int64_t>(*key))
    return runtime->fail("sequence index must be an integer");
  const auto index = position(*key, *size);
  if (!index)
    return runtime->fail("sequence index out of range");
  if (const auto* sequence = object<Sequence>(*value)) {
    return runtime->hold(sequence->items[*index]);
  }
  const auto& string = *as<std::string>(*value);
  std::size_t offset = 0;
  for (std::size_t step = 0; step < *index; ++step)
    offset += rune_size(string[offset]);
  return runtime->hold({string.substr(offset, rune_size(string[offset]))});
}

extern "C" const Value* ctk_jit_value_slice_v1(Values* runtime, const Value* value,
                                               const Value* start, const Value* stop,
                                               const Value* step) {
  if (object<Record>(*value))
    return runtime->fail("record is not sliceable");
  const auto size = length(*value);
  if (!size)
    return runtime->fail("value is not sliceable");
  auto bound = [](const Value* operand) -> std::optional<std::int64_t> {
    if (operand) {
      if (const auto* integer = as<std::int64_t>(*operand))
        return *integer;
    }
    return std::nullopt;
  };
  const auto first = bound(start);
  const auto last = bound(stop);
  const auto stride = bound(step);
  if ((start && !first) || (stop && !last) || (step && !stride)) {
    return runtime->fail("slice bounds must be integers");
  }
  const auto increment = stride.value_or(1);
  if (!increment)
    return runtime->fail("slice step must not be zero");
  const auto count = static_cast<std::int64_t>(*size);
  const bool reverse = increment < 0;
  auto normalize = [&](std::optional<std::int64_t> input, std::int64_t default_value) {
    if (!input)
      return default_value;
    auto index = *input;
    if (index < 0)
      index += count;
    return std::clamp(index, reverse ? std::int64_t{-1} : 0, reverse ? count - 1 : count);
  };
  auto index = normalize(first, reverse ? count - 1 : 0);
  const auto end = normalize(last, reverse ? -1 : count);
  std::vector<Value> items;
  while (reverse ? index > end : index < end) {
    if (items.size() >= max_items)
      return runtime->fail("slice exceeds item limit");
    if (!runtime->tick())
      return nullptr;
    const Value key{index};
    const auto* item = ctk_jit_value_index_v1(runtime, value, &key);
    if (!item)
      return nullptr;
    items.push_back(*item);
    if (llvm::AddOverflow(index, increment, index))
      break;
  }
  return runtime->hold(list(std::move(items)));
}

extern "C" const Value* ctk_jit_value_pattern_v1(Values* runtime, const Value* value,
                                                 std::int32_t kind, std::int64_t size) {
  const auto* sequence = object<Sequence>(*value);
  const auto count = static_cast<std::size_t>(size);
  if (sequence && sequence->tuple == (kind == 1) &&
      (kind == 2 ? sequence->items.size() >= count : sequence->items.size() == count)) {
    return value;
  }
  return runtime->fail("destructuring pattern does not match");
}

extern "C" const Value* ctk_jit_value_tail_v1(Values* runtime, const Value* value) {
  const auto& items = object<Sequence>(*value)->items;
  return runtime->hold(list(std::vector<Value>(items.begin() + 1, items.end())));
}

extern "C" const Value* ctk_jit_value_store_v1(Values* runtime, const Value* value,
                                               const Value* key, const Value* item) {
  if (auto* sequence = object<Sequence>(*value)) {
    if (sequence->tuple)
      return runtime->fail("tuples are immutable");
    const auto index = position(*key, sequence->items.size());
    if (!index)
      return runtime->fail("invalid list index");
    if (references(*item, sequence, nullptr))
      return runtime->fail("cyclic collection");
    sequence->items[*index] = *item;
    return item;
  }
  if (!object<Record>(*value))
    return runtime->fail("assignment requires a list or record");
  return ctk_jit_value_add_v1(runtime, value, key, item) ? item : nullptr;
}

extern "C" const Value* ctk_jit_value_binding_test_v1(Values* runtime, const char* name,
                                                      std::int32_t test_set, std::int32_t negate) {
  const auto* value = runtime->lookup(name);
  const bool result = value && (!test_set || !std::holds_alternative<std::monostate>(value->data));
  return runtime->hold({negate ? !result : result});
}

extern "C" const Value* ctk_jit_value_predicate_v1(Values* runtime, const char* test,
                                                   const Value* left, const Value* right) {
  const llvm::StringRef op(test);
  if (op == "has" || op == "does_not_have") {
    const auto* key = as<std::string>(*right);
    if (!key)
      return runtime->fail("field name must be a string");
    bool present;
    if (const auto* data = object<Record>(*left)) {
      present = data->fields.contains(*key);
    } else if (const auto* node = object<NativeNode>(*left)) {
      present = node_property(*node, *key).has_value();
    } else {
      return runtime->fail("field presence requires a record or AST node");
    }
    return runtime->hold({op == "has" ? present : !present});
  }
  if (op == "is_kind" || op == "is_not_kind") {
    const auto* node = object<NativeNode>(*left);
    const auto* kind = as<std::string>(*right);
    if (!node || !kind)
      return runtime->fail("node kind requires a selected AST node");
    const llvm::StringRef expected =
        *kind == "CXXRecord" ? llvm::StringRef("CXXRecordDecl") : llvm::StringRef(*kind);
    const bool equal = node->node->getNodeKind().asStringRef() == expected;
    return runtime->hold({op == "is_kind" ? equal : !equal});
  }
  const auto* sequence = object<Sequence>(*right);
  if (!sequence || sequence->tuple)
    return runtime->fail("membership requires a plain list");
  if (!scalar(*left))
    return runtime->fail("membership requires scalar values");
  bool found = false;
  for (const auto& item : sequence->items) {
    if (!runtime->tick())
      return nullptr;
    if (!scalar(item))
      return runtime->fail("membership requires scalar values");
    const auto* equal = binary(*runtime, "==", *left, item);
    if (!equal)
      return nullptr;
    if (*as<bool>(*equal)) {
      found = true;
      break;
    }
  }
  return runtime->hold({op == "in" ? found : !found});
}

extern "C" const Value* ctk_jit_value_iterate_v1(Values* runtime, const Value* value) {
  if (object<Sequence>(*value))
    return value;
  std::vector<Value> items;
  if (const auto* data = object<Record>(*value)) {
    for (const auto& key : data->keys)
      items.push_back({key});
  } else if (const auto* string = as<std::string>(*value)) {
    for (std::size_t offset = 0; offset < string->size();) {
      const auto bytes = rune_size((*string)[offset]);
      items.push_back({string->substr(offset, bytes)});
      offset += bytes;
    }
  } else {
    return runtime->fail("foreach requires an iterable");
  }
  return runtime->hold(list(std::move(items)));
}

extern "C" std::int64_t ctk_jit_value_size_v1(Values*, const Value* value) {
  return static_cast<std::int64_t>(*length(*value));
}

extern "C" const Value* ctk_jit_value_at_v1(Values* runtime, const Value* value,
                                            std::int64_t index) {
  const Value key{index};
  return ctk_jit_value_index_v1(runtime, value, &key);
}

extern "C" void ctk_jit_value_push_v1(Values* runtime) { runtime->push(); }

extern "C" void ctk_jit_value_pop_v1(Values* runtime) { runtime->pop(); }

extern "C" std::int32_t ctk_jit_value_tick_v1(Values* runtime) { return runtime->tick() ? 0 : -1; }

extern "C" void ctk_jit_value_unwind_v1(Values* runtime, std::int64_t depth) {
  runtime->scopes.resize(runtime->frame_depth + depth);
}

extern "C" void ctk_jit_value_clear_error_v1(Values* runtime) { runtime->error.clear(); }

extern "C" void ctk_jit_value_fail_v1(Values* runtime, const char* message) {
  runtime->fail(message);
}

extern "C" std::int32_t ctk_jit_value_recover_v1(Values* runtime) {
  if (runtime->fatal)
    return -1;
  runtime->error.clear();
  return 0;
}

extern "C" const Value* ctk_jit_value_save_error_v1(Values* runtime) {
  return runtime->hold({std::exchange(runtime->error, {})});
}

extern "C" void ctk_jit_value_restore_error_v1(Values* runtime, const Value* error) {
  runtime->error = *as<std::string>(*error);
}

extern "C" const Value* ctk_jit_value_runnable_v1(Values* runtime, const char* name,
                                                  RunnableEntry entry) {
  return runtime->hold(
      {std::make_shared<Runnable>(Runnable{name, entry, runtime->scopes, runtime->code})});
}

extern "C" const Value* ctk_jit_value_invoke_v1(Values* runtime, const Value* value,
                                                const Value* arguments, const Value* keywords) {
  const auto* runnable = object<Runnable>(*value);
  if (!runnable)
    return runtime->fail("value is not callable");
  if (runtime->call_depth >= 64)
    return runtime->fail("runnable call depth exceeds 64");
  auto previous_scopes = std::move(runtime->scopes);
  auto previous_code = std::exchange(runtime->code, runnable->code);
  runtime->scopes = runnable->captured;
  runtime->push();
  if (!runnable->name.empty())
    runtime->local().insert_or_assign(runnable->name, *value);
  const auto previous_depth = std::exchange(runtime->frame_depth, runtime->scopes.size());
  ++runtime->call_depth;
  const auto* result = runnable->entry(runtime->context, runtime, arguments, keywords);
  --runtime->call_depth;
  runtime->frame_depth = previous_depth;
  runtime->scopes = std::move(previous_scopes);
  runtime->code = std::move(previous_code);
  return result;
}

extern "C" std::int32_t ctk_jit_value_check_arguments_v1(Values* runtime, const Value* arguments,
                                                         const Value* keywords,
                                                         const char* const* labels,
                                                         std::int64_t count,
                                                         std::int64_t required) {
  const auto positional = object<Sequence>(*arguments)->items.size();
  const auto* named = object<Record>(*keywords);
  if (positional > static_cast<std::size_t>(count)) {
    runtime->fail("too many positional arguments");
    return -1;
  }
  for (const auto& key : named->keys) {
    bool found = false;
    for (std::int64_t index = 0; index < count; ++index) {
      if (!labels[index] || key != labels[index])
        continue;
      if (static_cast<std::size_t>(index) < positional) {
        runtime->fail(llvm::Twine("multiple values for parameter '") + key + "'");
        return -1;
      }
      found = true;
      break;
    }
    if (!found) {
      runtime->fail(llvm::Twine("unknown parameter '") + key + "'");
      return -1;
    }
  }
  for (auto index = static_cast<std::int64_t>(positional); index < required; ++index) {
    if (!labels[index] || !named->fields.contains(labels[index])) {
      runtime->fail("missing required argument");
      return -1;
    }
  }
  return 0;
}

extern "C" const Value* ctk_jit_value_argument_v1(Values* runtime, const Value* arguments,
                                                  const Value* keywords, std::int64_t index,
                                                  const char* label) {
  const auto& positional = object<Sequence>(*arguments)->items;
  if (static_cast<std::size_t>(index) < positional.size())
    return runtime->hold(positional[index]);
  if (label) {
    const auto& named = object<Record>(*keywords)->fields;
    if (const auto entry = named.find(label); entry != named.end()) {
      return runtime->hold(entry->second);
    }
  }
  return nullptr;
}

const Value* range(Values* runtime, const std::vector<Value>& args) {
  if (args.empty() || args.size() > 3 ||
      llvm::any_of(args, [](const Value& value) { return !as<std::int64_t>(value); })) {
    return runtime->fail("range accepts one to three integer arguments");
  }
  auto start = args.size() == 1 ? 0 : *as<std::int64_t>(args[0]);
  const auto stop = *as<std::int64_t>(args[args.size() == 1 ? 0 : 1]);
  const auto step = args.size() == 3 ? *as<std::int64_t>(args[2]) : 1;
  if (step == 0)
    return runtime->fail("range step must not be zero");
  std::vector<Value> items;
  while (step > 0 ? start < stop : start > stop) {
    if (items.size() == max_items)
      return runtime->fail("range exceeds item limit");
    items.push_back({start});
    if (llvm::AddOverflow(start, step, start))
      break;
  }
  return runtime->hold(list(std::move(items)));
}

const Value* collection_filter(Values* runtime, llvm::StringRef name,
                               const std::vector<Value>& args) {
  if (args.empty())
    return runtime->fail("collection filter requires a value");
  if (name == "keys" || name == "values" || name == "entries") {
    const auto* data = object<Record>(args[0]);
    if (!data || args.size() != 1)
      return runtime->fail("mapping filter requires one record");
    std::vector<Value> result;
    for (const auto& key : data->keys) {
      const auto& value = data->fields.find(key)->second;
      if (name == "keys")
        result.push_back({key});
      else if (name == "values")
        result.push_back(value);
      else {
        auto entry = std::make_shared<Record>();
        entry->set("key", {key});
        entry->set("value", value);
        result.push_back({std::move(entry)});
      }
    }
    return runtime->hold(list(std::move(result)));
  }
  const auto* sequence = object<Sequence>(args[0]);
  if (!sequence)
    return runtime->fail("collection filter requires a list or tuple");
  const auto& items = sequence->items;
  if (name == "map" || name == "filter") {
    if (args.size() != 2 || !object<Runnable>(args[1])) {
      return runtime->fail("map and filter require a runnable callback");
    }
    const auto empty_keywords = record();
    std::vector<Value> result;
    for (std::size_t index = 0; index < items.size(); ++index) {
      if (!runtime->tick())
        return nullptr;
      if (index >= max_items)
        return runtime->fail("callback filter exceeds item limit");
      const auto item = items[index];
      const auto argument = list({item});
      const auto* value = ctk_jit_value_invoke_v1(runtime, &args[1], &argument, &empty_keywords);
      if (!value)
        return nullptr;
      if (name == "map") {
        result.push_back(*value);
      } else if (const auto* flag = as<bool>(*value)) {
        if (*flag)
          result.push_back(item);
      } else {
        return runtime->fail("filter callback must return bool");
      }
    }
    return runtime->hold(list(std::move(result)));
  }
  if (name == "take" || name == "drop" || name == "first" || name == "last") {
    const bool endpoint = name == "first" || name == "last";
    if (endpoint && args.size() == 1) {
      return runtime->hold(items.empty()     ? Value{}
                           : name == "first" ? items.front()
                                             : items.back());
    }
    const auto* count = args.size() == 2 ? as<std::int64_t>(args[1]) : nullptr;
    if (!count || *count < 0)
      return runtime->fail("collection count must be nonnegative");
    const auto size = std::min<std::uint64_t>(*count, items.size());
    auto first = items.begin();
    auto last = items.end();
    if (name == "drop")
      first += size;
    else if (name == "last")
      first = last - size;
    else
      last = first + size;
    return runtime->hold(list(std::vector<Value>(first, last)));
  }
  if (name == "join") {
    const auto* separator = args.size() == 2 ? as<std::string>(args[1]) : nullptr;
    if (args.size() > 2 || (args.size() == 2 && !separator)) {
      return runtime->fail("join separator must be a string");
    }
    std::string result;
    for (std::size_t index = 0; index < items.size(); ++index) {
      const auto* part = as<std::string>(items[index]);
      if (!part)
        return runtime->fail("join requires string items");
      if (index && separator)
        result += *separator;
      result += *part;
    }
    return runtime->hold({std::move(result)});
  }
  if (args.size() != 1)
    return runtime->fail("collection filter requires one argument");
  if (name == "flatten") {
    std::vector<Value> result;
    for (const auto& item : items) {
      const auto* nested = object<Sequence>(item);
      if (!nested)
        return runtime->fail("flatten requires nested collections");
      if (nested->items.size() > max_items - result.size()) {
        return runtime->fail("flatten exceeds item limit");
      }
      result.insert(result.end(), nested->items.begin(), nested->items.end());
    }
    return runtime->hold(list(std::move(result)));
  }
  if (name == "reverse") {
    return runtime->hold(list(std::vector<Value>(items.rbegin(), items.rend())));
  }
  return runtime->hold(list(items, name == "to_tuple"));
}

const Value* string_filter(Values* runtime, llvm::StringRef name, const std::vector<Value>& args) {
  const auto* value = args.empty() ? nullptr : as<std::string>(args[0]);
  const auto* argument = args.size() == 2 ? as<std::string>(args[1]) : nullptr;
  if (!value || !argument)
    return runtime->fail("string filter requires two strings");
  const llvm::StringRef text(*value);
  if (name == "starts_with")
    return runtime->hold({text.starts_with(*argument)});
  if (name == "ends_with")
    return runtime->hold({text.ends_with(*argument)});
  if (name == "contains")
    return runtime->hold({text.contains(*argument)});
  if (name == "strip_prefix") {
    return runtime->hold(
        {text.starts_with(*argument) ? text.drop_front(argument->size()).str() : *value});
  }
  if (name == "strip_suffix") {
    return runtime->hold(
        {text.ends_with(*argument) ? text.drop_back(argument->size()).str() : *value});
  }
  if (argument->empty())
    return runtime->fail("split separator must be nonempty");
  llvm::SmallVector<llvm::StringRef> parts;
  text.split(parts, *argument, max_items);
  if (parts.size() > max_items)
    return runtime->fail("split exceeds item limit");
  std::vector<Value> result;
  for (auto part : parts)
    result.push_back({part.str()});
  return runtime->hold(list(std::move(result)));
}

extern "C" const Value* ctk_jit_value_call_v1(Values* runtime, const char* name,
                                              const Value* arguments, const Value* keywords) {
  const auto& args = object<Sequence>(*arguments)->items;
  if (const auto* callee = runtime->lookup(name)) {
    return ctk_jit_value_invoke_v1(runtime, runtime->hold(*callee), arguments, keywords);
  }
  if (!object<Record>(*keywords)->keys.empty()) {
    return runtime->fail("built-in does not accept keyword arguments");
  }
  const llvm::StringRef function(name);
  if (function == "len" || function == "length") {
    const auto size = args.size() == 1 ? length(args.front()) : std::nullopt;
    if (size && *size <= max_items)
      return runtime->hold({static_cast<std::int64_t>(*size)});
    return runtime->fail("len requires a sized value within the item limit");
  }
  if (function == "range")
    return range(runtime, args);
  if (function == "map" || function == "filter" || function == "take" || function == "drop" ||
      function == "first" || function == "last" || function == "keys" || function == "values" ||
      function == "entries" || function == "flatten" || function == "reverse" ||
      function == "to_list" || function == "to_tuple" || function == "join") {
    return collection_filter(runtime, function, args);
  }
  if (function == "split_by" || function == "starts_with" || function == "ends_with" ||
      function == "contains" || function == "strip_prefix" || function == "strip_suffix") {
    return string_filter(runtime, function, args);
  }
  return runtime->fail(llvm::Twine("undefined callable '") + name + "'");
}

extern "C" const Value* ctk_jit_value_method_v1(Values* runtime, const Value* base,
                                                const char* method, const Value* arguments) {
  const auto& args = object<Sequence>(*arguments)->items;
  const llvm::StringRef name(method);
  if (name == "hasField" && args.size() == 1) {
    return ctk_jit_value_predicate_v1(runtime, "has", base, &args[0]);
  }
  if (auto* sequence = object<Sequence>(*base)) {
    if (name == "one" && args.size() <= 1) {
      if (sequence->items.size() == 1)
        return runtime->hold(sequence->items[0]);
      return runtime->fail("one requires exactly one item");
    }
    if (!sequence->tuple) {
      if (name == "push" && args.size() == 1) {
        return ctk_jit_value_add_v1(runtime, base, nullptr, &args[0]);
      }
      if (name == "pop" && args.size() <= 1) {
        const Value last{std::int64_t{-1}};
        const auto index = position(args.empty() ? last : args[0], sequence->items.size());
        if (!index)
          return runtime->fail("list pop index out of range");
        auto selected = std::move(sequence->items[*index]);
        sequence->items.erase(sequence->items.begin() + *index);
        return runtime->hold(std::move(selected));
      }
      if (name == "clear" && args.empty()) {
        sequence->items.clear();
        return base;
      }
      if (name == "joinWith" && args.size() == 1) {
        const auto* separator = as<std::string>(args[0]);
        if (!separator)
          return runtime->fail("joinWith requires a string separator");
        std::string result;
        llvm::raw_string_ostream output(result);
        for (std::size_t index = 0; index < sequence->items.size(); ++index) {
          if (index)
            output << *separator;
          format(output, sequence->items[index], false);
        }
        return runtime->hold({std::move(result)});
      }
    }
  }
  if (auto* data = object<Record>(*base)) {
    if (name == "clear" && args.empty()) {
      data->fields.clear();
      data->keys.clear();
      return base;
    }
    if (name == "set" && args.size() == 2) {
      return ctk_jit_value_store_v1(runtime, base, &args[0], &args[1]);
    }
    const auto* key = args.empty() ? nullptr : as<std::string>(args[0]);
    if (key) {
      const auto found = data->fields.find(*key);
      if (name == "get" && args.size() <= 2) {
        return runtime->hold(found != data->fields.end() ? found->second
                             : args.size() == 2          ? args[1]
                                                         : Value{});
      }
      if (name == "hasKey" && args.size() == 1) {
        return runtime->hold({found != data->fields.end()});
      }
      if (name == "delete" && args.size() == 1) {
        if (found == data->fields.end())
          return runtime->fail("dictionary key not found");
        auto result = std::move(found->second);
        data->fields.erase(found);
        std::erase(data->keys, *key);
        return runtime->hold(std::move(result));
      }
    }
  }
  return runtime->fail(llvm::Twine("invalid collection method '") + name + "'");
}

extern "C" const Value* ctk_jit_value_matcher_v1(Values* runtime, const char* name,
                                                 const Value* arguments, const Value* binding) {
  std::string text;
  llvm::raw_string_ostream output(text);
  output << name << '(';
  llvm::StringRef separator;
  for (const auto& arg : object<Sequence>(*arguments)->items) {
    if ((!scalar(arg) || std::holds_alternative<std::monostate>(arg.data)) &&
        !as<MatcherValue>(arg)) {
      return runtime->fail("matcher arguments require a matcher, number, string or bool");
    }
    output << separator;
    format(output, arg, true);
    separator = ", ";
  }
  output << ')';
  if (binding) {
    if (!as<std::string>(*binding))
      return runtime->fail("matcher binding requires a string");
    output << ".bind(";
    format(output, *binding, true);
    output << ')';
  }
  return runtime->hold({MatcherValue{std::move(text)}});
}

extern "C" const Value* ctk_jit_value_bind_matcher_v1(Values* runtime, const Value* value,
                                                      const Value* binding) {
  const auto* matcher = as<MatcherValue>(*value);
  const auto* name = as<std::string>(*binding);
  if (!matcher || !name)
    return runtime->fail("bind requires a matcher and a string");
  std::string text = matcher->text;
  llvm::raw_string_ostream output(text);
  output << ".bind(" << llvm::json::Value(*name) << ')';
  return runtime->hold({MatcherValue{std::move(text)}});
}

extern "C" const Value* ctk_jit_value_render_v1(Values* runtime, const Value* value) {
  std::string text;
  llvm::raw_string_ostream output(text);
  format(output, *value, false);
  return runtime->hold({std::move(text)});
}

extern "C" void ctk_jit_value_print_v1(Values* runtime, const Value* value) {
  llvm::raw_string_ostream output(runtime->output);
  format(output, *value, false);
  output << '\n';
}

extern "C" std::int64_t ctk_jit_value_output_size_v1(Values* runtime) {
  return static_cast<std::int64_t>(runtime->output.size());
}

extern "C" void ctk_jit_value_display_v1(Values* runtime, const Value* value, std::int64_t offset) {
  if (!std::holds_alternative<std::monostate>(value->data) &&
      offset == ctk_jit_value_output_size_v1(runtime)) {
    ctk_jit_value_print_v1(runtime, value);
  }
}

} // namespace

void Record::set(llvm::StringRef key, Value value) {
  if (!fields.contains(key))
    keys.push_back(key.str());
  fields.insert_or_assign(key, std::move(value));
}

llvm::Error expose_values(llvm::orc::LLJIT& jit) {
  llvm::orc::SymbolMap symbols;
  auto expose = [&](llvm::StringRef name, auto* function) {
    symbols[jit.mangleAndIntern(name)] = {llvm::orc::ExecutorAddr::fromPtr(function),
                                          llvm::JITSymbolFlags::Exported |
                                              llvm::JITSymbolFlags::Callable};
  };
#define EXPOSE(name) expose(#name, &name)
  EXPOSE(ctk_jit_value_literal_v1);
  EXPOSE(ctk_jit_value_lookup_v1);
  EXPOSE(ctk_jit_value_define_v1);
  EXPOSE(ctk_jit_value_assign_v1);
  EXPOSE(ctk_jit_value_binary_v1);
  EXPOSE(ctk_jit_value_unary_v1);
  EXPOSE(ctk_jit_value_truth_v1);
  EXPOSE(ctk_jit_value_new_v1);
  EXPOSE(ctk_jit_value_add_v1);
  EXPOSE(ctk_jit_value_get_v1);
  EXPOSE(ctk_jit_value_index_v1);
  EXPOSE(ctk_jit_value_store_v1);
  EXPOSE(ctk_jit_value_slice_v1);
  EXPOSE(ctk_jit_value_pattern_v1);
  EXPOSE(ctk_jit_value_tail_v1);
  EXPOSE(ctk_jit_value_binding_test_v1);
  EXPOSE(ctk_jit_value_predicate_v1);
  EXPOSE(ctk_jit_value_iterate_v1);
  EXPOSE(ctk_jit_value_size_v1);
  EXPOSE(ctk_jit_value_at_v1);
  EXPOSE(ctk_jit_value_push_v1);
  EXPOSE(ctk_jit_value_pop_v1);
  EXPOSE(ctk_jit_value_tick_v1);
  EXPOSE(ctk_jit_value_call_v1);
  EXPOSE(ctk_jit_value_method_v1);
  EXPOSE(ctk_jit_value_runnable_v1);
  EXPOSE(ctk_jit_value_unwind_v1);
  EXPOSE(ctk_jit_value_clear_error_v1);
  EXPOSE(ctk_jit_value_fail_v1);
  EXPOSE(ctk_jit_value_recover_v1);
  EXPOSE(ctk_jit_value_save_error_v1);
  EXPOSE(ctk_jit_value_restore_error_v1);
  EXPOSE(ctk_jit_value_invoke_v1);
  EXPOSE(ctk_jit_value_check_arguments_v1);
  EXPOSE(ctk_jit_value_argument_v1);
  EXPOSE(ctk_jit_value_matcher_v1);
  EXPOSE(ctk_jit_value_bind_matcher_v1);
  EXPOSE(ctk_jit_value_render_v1);
  EXPOSE(ctk_jit_value_print_v1);
  EXPOSE(ctk_jit_value_output_size_v1);
  EXPOSE(ctk_jit_value_display_v1);
#undef EXPOSE
  return jit.getMainJITDylib().define(llvm::orc::absoluteSymbols(std::move(symbols)));
}

} // namespace ctk::jit
