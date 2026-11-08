#include "values.hpp"
#include "workspace.hpp"
#include "platform/repl_cancellation.hpp"
#include "file_values.hpp"
#include "semantic.hpp"
#include "documents.hpp"
#include "filters.hpp"
#include "value_access.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <utility>

#include <clang/AST/ASTContext.h>
#include <clang/AST/ASTTypeTraits.h>
#include <clang/AST/DeclCXX.h>
#include <clang/AST/Stmt.h>
#include <clang/Basic/SourceManager.h>
#include <llvm/ADT/SmallPtrSet.h>
#include <llvm/ExecutionEngine/Orc/LLJIT.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/MathExtras.h>

namespace ctk::jit {
using namespace value_access;

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
  if (workspace && repl_cancelled()) {
    fatal = true;
    fail("operation cancelled");
    return false;
  }
  if (++steps > 1000000) {
    fatal = true;
    fail("execution step limit exceeded");
    return false;
  }
  return true;
}

namespace {

template <typename T> Value related(const NativeNode& original, const T& node) {
  return {std::make_shared<NativeNode>(NativeNode{
      original.ast, std::make_shared<clang::DynTypedNode>(clang::DynTypedNode::create(node))})};
}

std::optional<Value> node_property(const NativeNode& native, llvm::StringRef key) {
  const auto& node = *native.node;
  if (key == "kind" || key == "clang_kind")
    return Value{node.getNodeKind().asStringRef().str()};
  if (key == "source_file") {
    if (auto path = native_source_file(native.ast))
      return Value{std::move(*path)};
    return Value{};
  }
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
  } else if (const auto* entry = object<FileEntry>(value)) {
    if (quote)
      out << llvm::json::Value(entry->absolute);
    else
      out << entry->path;
  } else if (const auto* matcher = as<MatcherValue>(value)) {
    out << matcher->text;
  } else if (const auto* runnable = object<Runnable>(value)) {
    out << runnable->name;
  } else if (const auto* builtin = as<BuiltinFunction>(value)) {
    out << builtin->name;
  } else {
    out << "null";
  }
}

enum class Render { Console, Json, Tuple };

void quote_tuple(llvm::raw_ostream& out, llvm::StringRef string) {
  const auto quote = string.contains('\'') && !string.contains('"') ? '"' : '\'';
  out << quote;
  for (const unsigned char ch : string) {
    if (ch == quote || ch == '\\')
      out << '\\' << ch;
    else if (ch == '\n')
      out << "\\n";
    else if (ch == '\r')
      out << "\\r";
    else if (ch == '\t')
      out << "\\t";
    else if (ch < 0x20 || ch == 0x7f) {
      const char hex[] = "0123456789abcdef";
      out << "\\x" << hex[ch >> 4] << hex[ch & 0xf];
    } else
      out << ch;
  }
  out << quote;
}

void render(llvm::raw_ostream& out, const Value& value, Render style, unsigned depth = 0) {
  if (depth >= 16) {
    out << (style == Render::Json ? R"({"…": "maximum depth reached"})" : "… <truncated>");
    return;
  }
  if (const auto* text = as<std::string>(value)) {
    if (style == Render::Tuple)
      quote_tuple(out, *text);
    else if (style == Render::Json)
      out << llvm::json::Value(*text);
    else
      out << *text;
  } else if (const auto* number = as<double>(value)) {
    out << format_float(*number);
  } else if (const auto* flag = as<bool>(value)) {
    if (style == Render::Tuple)
      out << (*flag ? "True" : "False");
    else
      out << (*flag ? "true" : "false");
  } else if (std::holds_alternative<std::monostate>(value.data)) {
    out << (style == Render::Json ? "null" : "None");
  } else if (const auto* sequence = object<Sequence>(value)) {
    const bool tuple = sequence->tuple;
    if (tuple && style == Render::Json) {
      out << R"({"type": "tuple"})";
      return;
    }
    const bool lines = !tuple && style == Render::Console;
    if (!lines)
      out << (tuple ? '(' : '[');
    const auto size = style == Render::Json ? std::min<std::size_t>(20, sequence->items.size())
                                            : sequence->items.size();
    for (std::size_t index = 0; index < size; ++index) {
      if (index)
        out << (lines ? "\n" : ", ");
      render(out, sequence->items[index], tuple ? Render::Tuple : style, depth + 1);
      if (out.tell() > 20000 && lines)
        break;
    }
    if (tuple && size == 1)
      out << ',';
    if (style == Render::Json && size < sequence->items.size())
      out << ", {\"truncated_items\": " << sequence->items.size() - size << '}';
    if (!lines)
      out << (tuple ? ')' : ']');
  } else if (const auto* mapping = object<Record>(value)) {
    auto keys = mapping->keys;
    if (style != Render::Tuple) {
      if (keys.size() > 20)
        keys.resize(20);
      llvm::sort(keys);
    }
    out << '{';
    bool first = true;
    for (const auto& key : keys) {
      if (!first)
        out << ", ";
      first = false;
      if (style == Render::Tuple)
        quote_tuple(out, key);
      else
        out << llvm::json::Value(key);
      out << ": ";
      render(out, mapping->fields.find(key)->second,
             style == Render::Tuple ? Render::Tuple : Render::Json, depth + 1);
    }
    if (keys.size() < mapping->keys.size())
      out << ", \"truncated_items\": " << mapping->keys.size() - keys.size();
    out << '}';
  } else if (const auto* entry = object<FileEntry>(value)) {
    if (style == Render::Json)
      render(out, file_record(*entry), style, depth);
    else out << entry->path;
  } else if (const auto* view = object<SemanticValue>(value)) {
    out << llvm::StringRef(semantic_json(*view, style == Render::Console)).rtrim("\n");
  } else if (const auto* flag = as<SemanticEnum>(value)) {
    if (style == Render::Json) out << llvm::json::Value(flag->name);
    else out << flag->name;
  } else if (const auto* ast = as<AstHandle>(value)) {
    const auto& sources = (*ast)->getSourceManager();
    const auto file = sources.getFileEntryRefForID(sources.getMainFileID());
    out << "parsed " << (file ? file->getName() : llvm::StringRef("<input>"));
  } else {
    format(out, value, false);
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
  if (is_builtin(name))
    return runtime->hold({BuiltinFunction{name}});
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

const Value* hold_semantic(Values& runtime, llvm::Expected<Value> value) {
  return value ? runtime.hold(std::move(*value)) : runtime.fail(llvm::toString(value.takeError()));
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
    if (data->match_row) {
      if (property == "source_file")
        return runtime->hold(data->source_file ? Value{*data->source_file} : Value{});
      if (property == "source_match_index")
        return runtime->hold(data->source_match_index ? Value{*data->source_match_index} : Value{});
      if (property == "bindings") {
        auto bindings = std::make_shared<Record>();
        for (const auto& name : data->keys)
          if (const auto* node = object<NativeNode>(data->fields.at(name)))
            bindings->set(name, {semantic(*node)});
        return runtime->hold({std::move(bindings)});
      }
    }
    if (const auto found = data->fields.find(key); found != data->fields.end()) {
      return runtime->hold(found->second);
    }
    return runtime->fail(llvm::Twine("no record field named '") + key + "'");
  }
  if (const auto* entry = object<FileEntry>(*value)) {
    if (auto field = file_field(*entry, property))
      return runtime->hold(std::move(*field));
  }
  if (const auto* node = object<NativeNode>(*value)) {
    if (property == "value") {
      auto view = semantic(*node);
      return view ? runtime->hold({std::move(view)}) : runtime->fail("native node is unavailable");
    }
    if (auto field = node_property(*node, property))
      return runtime->hold(std::move(*field));
    if (const auto view = semantic(*node))
      return hold_semantic(*runtime, semantic_field(*view, property));
  }
  if (const auto* view = object<SemanticValue>(*value))
    return hold_semantic(*runtime, semantic_field(*view, property));
  if (const auto* flag = as<SemanticEnum>(*value)) {
    if (property == "name") return runtime->hold({flag->name});
    if (property == "number") return runtime->hold({flag->number});
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
  if (object<SemanticValue>(*value) || object<NativeNode>(*value)) {
    const auto* field = as<std::string>(*key);
    if (!field) return runtime->fail("semantic field requires a string key");
    return ctk_jit_value_get_v1(runtime, value, field->c_str(), nullptr);
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

bool contains_live_batch_value(const Value& value, unsigned depth = 0) {
  if (depth >= 64 || as<AstHandle>(value) || object<NativeNode>(value) ||
      object<Runnable>(value) || semantic_has_live_resource(value))
    return true;
  if (const auto* items = object<Sequence>(value)) {
    for (const auto& item : items->items)
      if (contains_live_batch_value(item, depth + 1)) return true;
  } else if (const auto* record = object<Record>(value)) {
    for (const auto& [key, item] : record->fields)
      if (contains_live_batch_value(item, depth + 1)) return true;
  }
  return false;
}

extern "C" const Value* ctk_jit_value_store_v1(Values* runtime, const Value* value,
                                               const Value* key, const Value* item) {
  if (runtime->state.batch_output_bytes && contains_live_batch_value(*item))
    return runtime->fail("batch collection updates cannot retain live resources");
  if (auto* sequence = object<Sequence>(*value)) {
    if (sequence->semantic_collection)
      return runtime->fail("semantic collections are immutable");
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
  const auto* record = object<Record>(*value);
  if (!record)
    return runtime->fail("assignment requires a list or record");
  if (record->semantic_collection)
    return runtime->fail("semantic collections are immutable");
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
    } else {
      const auto* view = object<SemanticValue>(*left);
      const auto* node = object<NativeNode>(*left);
      const auto pinned = node ? semantic(*node) : nullptr;
      if (!view) view = pinned.get();
      if (!view) return runtime->fail("field presence requires a record or AST node");
      auto result = semantic_method(*view, "hasField", Sequence{{*right}});
      if (!result) return runtime->fail(llvm::toString(result.takeError()));
      present = *as<bool>(*result);
    }
    return runtime->hold({op == "has" ? present : !present});
  }
  if (op == "is_kind" || op == "is_not_kind") {
    const auto* node = object<NativeNode>(*left);
    const auto* kind = as<std::string>(*right);
    if (kind && (*kind == "File" || *kind == "Directory" || *kind == "FileSystemEntry")) {
      const auto* entry = object<FileEntry>(*left);
      const bool equal = entry && (*kind == "FileSystemEntry" ||
                                   (*kind == "Directory") == entry->directory);
      return runtime->hold({op == "is_kind" ? equal : !equal});
    }
    if (const auto* view = object<SemanticValue>(*left); view && kind) {
      const bool equal = semantic_kind(*view, *kind);
      return runtime->hold({op == "is_kind" ? equal : !equal});
    }
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
  if (auto iterable = semantic_iteration(*value))
    return runtime->hold(std::move(*iterable));
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

extern "C" const Value* ctk_jit_value_runnable_v2(Values* runtime, const char* name,
                                                  RunnableEntry entry, std::uint64_t minimum,
                                                  std::uint64_t maximum) {
  return runtime->hold({std::make_shared<Runnable>(Runnable{
      name, entry, minimum, maximum, runtime->source_path, runtime->scopes, runtime->code})});
}

} // namespace

const Value* Values::property(const Value& value, const char* name) {
  return ctk_jit_value_get_v1(this, &value, name, nullptr);
}

const Value* Values::index(const Value& value, const Value& key) {
  return ctk_jit_value_index_v1(this, &value, &key);
}

extern "C" const Value* ctk_jit_value_invoke_v1(Values* runtime, const Value* value,
                                                const Value* arguments, const Value* keywords) {
  if (const auto* builtin = as<BuiltinFunction>(*value)) {
    return call_builtin(*runtime, builtin->name, object<Sequence>(*arguments)->items,
                        *object<Record>(*keywords));
  }
  const auto* runnable = object<Runnable>(*value);
  if (!runnable)
    return runtime->fail("value is not callable");
  if (runtime->call_depth >= 64)
    return runtime->fail("runnable call depth exceeds 64");
  auto previous_scopes = std::move(runtime->scopes);
  auto previous_code = std::exchange(runtime->code, runnable->code);
  auto previous_source = std::exchange(runtime->source_path, runnable->source_path);
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
  runtime->source_path = std::move(previous_source);
  return result;
}

namespace {

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

extern "C" void ctk_jit_value_match_location_v1(Values* runtime, std::uint64_t line,
                                                  std::uint64_t column) {
  if (auto* match = runtime->match_output) {
    match->line = line;
    match->column = column;
  }
}

extern "C" const Value* ctk_jit_value_match_bindings_v1(Values* runtime, const Value* bindings) {
  for (const auto& [name, value] : object<Record>(*bindings)->fields)
    runtime->local().insert_or_assign(name, value);
  return bindings;
}

extern "C" std::int32_t ctk_jit_value_exit_requested_v1(Values* runtime) {
  return runtime->exit_requested;
}

extern "C" void ctk_jit_value_exit_v1(Values* runtime) { runtime->exit_requested = true; }

extern "C" void ctk_jit_value_set_source_v1(Values* runtime, const char* path) {
  runtime->source_path = path;
}

extern "C" void ctk_jit_value_set_result_v1(Values* runtime, const Value* result) {
  runtime->result = result;
}

extern "C" const Value* ctk_jit_value_call_v1(Values* runtime, const char* name,
                                              const Value* arguments, const Value* keywords) {
  if (const auto* callee = runtime->lookup(name)) {
    return ctk_jit_value_invoke_v1(runtime, runtime->hold(*callee), arguments, keywords);
  }
  return call_builtin(*runtime, name, object<Sequence>(*arguments)->items,
                      *object<Record>(*keywords));
}

extern "C" const Value* ctk_jit_value_change_binding_v1(Values* runtime, const char* old_name,
                                                        const char* new_name) {
  auto& globals = runtime->globals;
  const auto old = globals.find(old_name);
  if (old == globals.end())
    return runtime->fail(llvm::Twine("undefined binding '") + old_name + "'");
  if (new_name && old->getKey() != new_name) {
    if (globals.contains(new_name))
      return runtime->fail(llvm::Twine("binding already exists: ") + new_name);
    auto value = std::move(old->second);
    globals.erase(old);
    globals.try_emplace(new_name, std::move(value));
  } else if (!new_name) {
    globals.erase(old);
  }
  return runtime->hold({});
}

extern "C" const Value* ctk_jit_value_bindings_v1(Values* runtime) {
  if (runtime->workspace && !runtime->consume_depth && runtime->state.output_path.empty()) {
    auto record = std::make_shared<Record>();
    record->fields = runtime->globals;
    if (runtime->workspace->capture(*runtime, "bindings_list", Value{std::move(record)}))
      return runtime->hold({std::string{}});
  }
  std::vector<llvm::StringRef> names;
  for (const auto& [name, value] : runtime->globals)
    names.push_back(name);
  llvm::sort(names);
  constexpr llvm::StringLiteral types[] = {
      "NoneType",    "bool",          "int",
      "float",       "str",           "list",
      "dict",        "ParsedTree",    "BindingSelection",
      "MatcherExpr", "RunnableBlock", "function", "MessageView", "EnumValue", "File",
  };
  std::size_t width = 0;
  for (auto name : names)
    width = std::max(width, name.size());
  std::string result = "Bindings";
  llvm::raw_string_ostream out(result);
  for (auto name : names) {
    const auto& value = runtime->globals.find(name)->second;
    const auto* sequence = object<Sequence>(value);
    auto type = sequence && sequence->tuple ? llvm::StringRef("tuple")
                                            : llvm::StringRef(types[value.data.index()]);
    if (const auto* entry = object<FileEntry>(value); entry && entry->directory) type = "Directory";
    out << "\n$" << name << std::string(width - name.size() + 2, ' ') << type;
  }
  return runtime->hold({std::move(result)});
}

extern "C" const Value* ctk_jit_value_method_v1(Values* runtime, const Value* base,
                                                const char* method, const Value* arguments) {
  const auto& parameters = *object<Sequence>(*arguments);
  const auto& args = parameters.items;
  const llvm::StringRef name(method);
  if (const auto* view = object<SemanticValue>(*base))
    return hold_semantic(*runtime, semantic_method(*view, name, parameters, runtime));
  if (const auto* node = object<NativeNode>(*base)) {
    if (const auto view = semantic(*node))
      return hold_semantic(*runtime, semantic_method(*view, name, parameters, runtime));
  }
  if (name == "hasField" && args.size() == 1) {
    return ctk_jit_value_predicate_v1(runtime, "has", base, &args[0]);
  }
  if (auto* sequence = object<Sequence>(*base)) {
    if (name == "one" && args.size() <= 1) {
      if (sequence->items.size() == 1)
        return runtime->hold(sequence->items[0]);
      return runtime->fail("one requires exactly one item");
    }
    if (!sequence->tuple && !sequence->semantic_collection) {
      if (name == "push" && args.size() == 1) {
        if (runtime->state.batch_output_bytes && contains_live_batch_value(args[0]))
          return runtime->fail("batch collection updates cannot retain live resources");
        return ctk_jit_value_add_v1(runtime, base, nullptr, &args[0]);
      }
      if (name == "delete" && args.size() == 1) {
        const auto* index = as<std::int64_t>(args[0]);
        if (!index || *index < 0 || static_cast<std::uint64_t>(*index) >= sequence->items.size())
          return runtime->fail("list deletion index out of range");
        sequence->items.erase(sequence->items.begin() + *index);
        return base;
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
          render(output, sequence->items[index], Render::Console);
        }
        return runtime->hold({std::move(result)});
      }
    }
  }
  if (auto* data = object<Record>(*base)) {
    if (name == "clear" && args.empty() && !data->semantic_collection) {
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
      if (name == "delete" && args.size() == 1 && !data->semantic_collection) {
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
  const auto& args = *object<Sequence>(*arguments);
  for (const auto& arg : args.items) {
    if ((!scalar(arg) || std::holds_alternative<std::monostate>(arg.data)) &&
        !as<MatcherValue>(arg) && !object<FileEntry>(arg))
      return runtime->fail("matcher arguments require a matcher, number, string, bool or file");
  }
  const auto* key = binding ? as<std::string>(*binding) : nullptr;
  if (binding && !key) return runtime->fail("matcher binding requires a string");
  return runtime->hold({matcher_value(name, args, key ? std::optional{*key} : std::nullopt)});
}

extern "C" const Value* ctk_jit_value_bind_matcher_v1(Values* runtime, const Value* value,
                                                      const Value* binding) {
  const auto* matcher = as<MatcherValue>(*value);
  const auto* name = as<std::string>(*binding);
  if (!matcher || !name)
    return runtime->fail("bind requires a matcher and a string");
  return runtime->hold({matcher_value(matcher->name, *matcher->arguments, *name)});
}

} // namespace

MatcherValue matcher_value(llvm::StringRef name, const Sequence& arguments,
                           std::optional<std::string> binding) {
  std::string text;
  llvm::raw_string_ostream output(text);
  output << name << '(';
  llvm::StringRef separator;
  for (const auto& arg : arguments.items) {
    output << separator;
    format(output, arg, true);
    separator = ", ";
  }
  output << ')';
  if (binding) output << ".bind(" << llvm::json::Value(*binding) << ')';
  return {std::move(text), name.str(), std::make_shared<Sequence>(arguments), std::move(binding)};
}

extern "C" const Value* ctk_jit_value_render_v1(Values* runtime, const Value* value) {
  const auto* seq = object<Sequence>(*value);
  const auto* record = object<Record>(*value);
  if (object<SemanticValue>(*value) || object<NativeNode>(*value) ||
      (seq && (seq->match_snapshot || seq->semantic_collection)) ||
      (record && (record->match_row || record->semantic_collection))) {
    if (auto text = runtime->present("render", *value))
      return runtime->hold({std::move(*text)});
  }
  std::string text;
  llvm::raw_string_ostream output(text);
  render(output, *value, Render::Console);
  if (text.size() > 20000) {
    std::size_t limit = 19980;
    while ((static_cast<unsigned char>(text[limit]) & 0xc0) == 0x80)
      --limit;
    text.resize(limit);
    text += "… <truncated>";
  }
  return runtime->hold({std::move(text)});
}

namespace {

extern "C" void ctk_jit_value_consume_begin_v1(Values* runtime) { ++runtime->consume_depth; }

extern "C" void ctk_jit_value_consume_end_v1(Values* runtime) { --runtime->consume_depth; }

extern "C" const Value* ctk_jit_value_print_v2(Values* runtime, const Value* value) {
  if (runtime->consume_depth)
    return value;
  if (runtime->workspace && runtime->workspace->capture(*runtime, "print", *value)) {
    runtime->last_printed = value;
    return value;
  }
  const auto* rendered = ctk_jit_value_render_v1(runtime, value);
  if (!rendered || !emit_text(*runtime, *as<std::string>(*rendered)))
    return nullptr;
  runtime->last_printed = value;
  return value;
}

extern "C" const Value* ctk_jit_value_print_match_v1(Values* runtime, const Value* value,
                                                     const char* key) {
  if (runtime->workspace && runtime->workspace->capture(*runtime, "match", *value, key)) {
    runtime->last_printed = value;
    return value;
  }
  return ctk_jit_value_print_v2(runtime, value);
}

extern "C" const Value* ctk_jit_value_help_v1(Values* runtime, const Value* value,
                                              const char* markdown) {
  if (runtime->workspace && !runtime->consume_depth && !runtime->match_output &&
      runtime->state.output_path.empty()) {
    runtime->previews.push_back({runtime->output.size(), -1, "help", {}, markdown});
    ++runtime->emissions;
    runtime->last_printed = value;
    return value;
  }
  return ctk_jit_value_print_v2(runtime, value);
}

extern "C" const Value* ctk_jit_value_inspect_v1(Values* runtime, const Value* value) {
  auto text = runtime->present("inspect", *value);
  const auto* preview = text ? runtime->hold({std::move(*text)})
                             : ctk_jit_value_render_v1(runtime, value);
  return preview && emit_text(*runtime, *as<std::string>(*preview)) ? preview : nullptr;
}

extern "C" std::int64_t ctk_jit_value_output_size_v1(Values* runtime) {
  return static_cast<std::int64_t>(runtime->emissions);
}

extern "C" const Value* ctk_jit_value_display_v2(Values* runtime, const Value* value,
                                                 std::int64_t offset, std::int32_t loop) {
  const bool emitted = offset != ctk_jit_value_output_size_v1(runtime);
  if (!std::holds_alternative<std::monostate>(value->data) &&
      !(emitted && (loop || runtime->last_printed == value))) {
    return ctk_jit_value_print_v2(runtime, value);
  }
  return value;
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
  EXPOSE(ctk_jit_value_set_source_v1);
  EXPOSE(ctk_jit_value_exit_v1);
  EXPOSE(ctk_jit_value_exit_requested_v1);
  EXPOSE(ctk_jit_value_match_bindings_v1);
  EXPOSE(ctk_jit_value_match_location_v1);
  EXPOSE(ctk_jit_value_set_result_v1);
  EXPOSE(ctk_jit_value_method_v1);
  EXPOSE(ctk_jit_value_bindings_v1);
  EXPOSE(ctk_jit_value_change_binding_v1);
  EXPOSE(ctk_jit_value_runnable_v2);
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
  EXPOSE(ctk_jit_value_print_v2);
  EXPOSE(ctk_jit_value_inspect_v1);
  EXPOSE(ctk_jit_value_help_v1);
  EXPOSE(ctk_jit_value_print_match_v1);
  EXPOSE(ctk_jit_value_consume_begin_v1);
  EXPOSE(ctk_jit_value_consume_end_v1);
  EXPOSE(ctk_jit_value_output_size_v1);
  EXPOSE(ctk_jit_value_display_v2);
#undef EXPOSE
  return jit.getMainJITDylib().define(llvm::orc::absoluteSymbols(std::move(symbols)));
}

} // namespace ctk::jit
