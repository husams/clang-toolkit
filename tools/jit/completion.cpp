#include "completion.hpp"

#include "file_values.hpp"
#include "grammar/syntax.hpp"
#include "semantic.hpp"
#include "value_access.hpp"

#include <algorithm>
#include <exception>
#include <filesystem>
#include <utility>

#include <llvm/ADT/STLExtras.h>
#include <llvm/ADT/SmallString.h>
#include <llvm/ADT/SmallVector.h>
#include <llvm/ADT/StringExtras.h>
#include <llvm/Support/Path.h>

namespace ctk::jit {
namespace {

using namespace value_access;
namespace json = llvm::json;
namespace fs = std::filesystem;

std::string escape_path(llvm::StringRef text, char quote) {
  std::string result;
  for (const unsigned char ch : text) {
    if (ch < 32 || ch == 127) {
      result += "\\x";
      result += llvm::hexdigit(ch >> 4);
      result += llvm::hexdigit(ch & 15);
      continue;
    }
    if (ch == '\\' || ch == quote)
      result += '\\';
    result += static_cast<char>(ch);
  }
  return result;
}

std::string path_prefix(llvm::StringRef atom, char quote) {
  std::size_t end = 1;
  while (end < atom.size() && atom[end] != quote) {
    if (atom[end] == '\\' && end + 1 < atom.size())
      ++end;
    ++end;
  }
  auto literal = atom.take_front(end).str() + quote;
  return decode_ctk_string(literal) + atom.drop_front(std::min(end + 1, atom.size())).str();
}

enum class TokenKind { Name, Dot, Dollar, Open, Close, Other };

struct Token {
  TokenKind kind;
  std::size_t begin;
};

bool identifier(char ch) { return llvm::isAlnum(ch) || ch == '_'; }

bool identifier(llvm::StringRef text) {
  return !text.empty() && !llvm::isDigit(text.front()) &&
         llvm::all_of(text, [](char ch) { return identifier(ch); });
}

const Syntax *single_child(const Syntax &node) {
  const Syntax *child = nullptr;
  for (const auto &part : node.children) {
    if (part.name == "proto_soft_newlines" || part.name == "proto_separators")
      continue;
    if (child)
      return nullptr;
    child = &part;
  }
  return child;
}

const Value *resolve(Values &values, const Syntax &node) {
  const llvm::StringRef kind(node.name);
  if (kind == "proto_reference")
    return node.children.empty() ? nullptr
                                 : values.lookup(node.children.back().text);

  if (kind == "proto_postfix") {
    const auto *value = resolve(values, node.children.front());
    for (const auto &part : llvm::drop_begin(node.children)) {
      if (!value)
        return nullptr;
      if (part.name == "proto_member_part") {
        value = values.property(*value,
                                std::string(part.children.back().text).c_str());
      } else if (part.name == "proto_index_expression") {
        const auto *expression = single_child(part);
        const auto *key = expression ? resolve(values, *expression) : nullptr;
        const auto *integer = key ? as<std::int64_t>(*key) : nullptr;
        value = key && (!integer || *integer >= 0) ? values.index(*value, *key)
                                                   : nullptr;
      } else {
        return nullptr;
      }
    }
    return value;
  }

  if (kind == "PROTO_INT" || kind == "LEGACY_NUMBER") {
    std::int64_t number = 0;
    if (!llvm::StringRef(node.text).getAsInteger(10, number))
      return values.hold({number});
    return nullptr;
  }

  if (kind == "PROTO_STRING" || kind == "LEGACY_STRING") {
    // Interpolation can evaluate arbitrary CTK. Only read literal keys here.
    if (node.text.starts_with('"') &&
        node.text.find_first_of("${}") != std::string_view::npos)
      return nullptr;
    return values.hold({decode_ctk_string(node.text)});
  }

  if (kind == "repl_start" || kind == "proto_start" ||
      kind == "proto_program" || kind == "proto_pipe_expr" ||
      kind == "proto_recovery_expr" || kind == "proto_comparison" ||
      kind == "proto_grouped_expression" || kind == "proto_inner_expression" ||
      kind == "proto_integer_literal" || kind == "proto_string_literal" ||
      kind == "host_expression" || kind == "display") {
    const auto *child = single_child(node);
    return child ? resolve(values, *child) : nullptr;
  }

  return nullptr;
}

void add(json::Array &fields, llvm::StringRef name,
         llvm::StringRef detail = "property", bool method = false) {
  if (identifier(name))
    fields.push_back(json::Object{
        {"name", name.str()}, {"detail", detail.str()}, {"method", method}});
}

void add_names(json::Array &fields, llvm::ArrayRef<llvm::StringRef> names,
               llvm::StringRef detail = "property", bool method = false) {
  for (const auto name : names)
    add(fields, name, detail, method);
}

constexpr llvm::StringLiteral binding_properties[] = {
    "name",      "value",           "scope",         "source_file", "decl_name",
    "decl_type", "parameter_name",  "record_name",   "type_name",   "location",
    "range",     "symbol_identity", "documentation", "call_site",
};

json::Array fields_for(const Value &value, bool presence) {
  json::Array fields;
  if (const auto *node = object<NativeNode>(value)) {
    if (presence)
      return fields;
    if (const auto view = semantic(*node)) {
      for (auto &field : semantic_completion_fields(*view)) {
        const auto name = field.getAsObject()->getString("name").value_or("");
        if (!llvm::is_contained(binding_properties, name))
          fields.push_back(std::move(field));
      }
    }
    for (const auto name : binding_properties)
      add(fields, name);
    return fields;
  }
  if (const auto *view = object<SemanticValue>(value))
    return semantic_completion_fields(*view, presence);
  if (presence)
    return fields;

  if (const auto *record = object<Record>(value)) {
    if (record->semantic_collection) {
      add_names(fields, {"length", "isEmpty", "keys"});
    } else if (record->match_row) {
      add_names(fields, {"bindings", "source_match_index", "source_file"});
      for (const auto &key : record->keys)
        add(fields, key);
    } else {
      for (const auto &key : record->keys)
        add(fields, key, "dictionary key");
      for (llvm::StringRef name : {"keys", "values", "length", "isEmpty"})
        if (!record->fields.contains(name))
          add(fields, name);
      add_names(fields, {"get", "set", "delete", "hasKey", "clear"}, "method",
                true);
    }
  } else if (const auto *sequence = object<Sequence>(value)) {
    if (sequence->semantic_collection) {
      add_names(fields, {"length", "isEmpty"});
    } else if (sequence->match_snapshot) {
      add_names(fields, {"length", "isEmpty"});
      add_names(fields, {"unique", "sort", "filter", "one"}, "method", true);
      for (const auto &item : sequence->items)
        if (const auto *row = object<Record>(item))
          for (const auto &key : row->keys)
            add(fields, key);
    } else if (!sequence->tuple) {
      add_names(fields, {"length", "isEmpty"});
      add_names(fields,
                {"push", "pop", "insert", "remove", "clear", "joinWith",
                 "unique", "sort", "filter", "one"},
                "method", true);
    }
  } else if (as<std::string>(value)) {
    add(fields, "strip", "method", true);
  } else if (as<SemanticEnum>(value)) {
    add_names(fields, {"name", "number"});
  } else if (object<FileEntry>(value)) {
    add_names(fields, {"absolute", "basename", "dirname", "modified", "parts",
                       "path", "size"});
  }
  return fields;
}

} // namespace

std::optional<llvm::StringRef> field_receiver(llvm::StringRef prefix) {
  // The Python editor applies this same bound before inspecting a reference.
  if (prefix.size() > 8192)
    return std::nullopt;

  llvm::SmallVector<Token, 32> tokens;
  for (std::size_t index = 0; index < prefix.size();) {
    const auto begin = index;
    const auto ch = prefix[index++];
    if (llvm::isSpace(ch))
      continue;
    auto kind = TokenKind::Other;
    if (identifier(ch)) {
      while (index < prefix.size() && identifier(prefix[index]))
        ++index;
      if (!llvm::isDigit(ch))
        kind = TokenKind::Name;
    } else if (ch == '\'' || ch == '"' || ch == '`') {
      while (index < prefix.size()) {
        const auto part = prefix[index++];
        if (part == ch)
          break;
        if (part == '\\' && index < prefix.size())
          ++index;
      }
    } else if (ch == '#' || prefix.substr(begin, 2) == "//") {
      while (index < prefix.size() && prefix[index] != '\n')
        ++index;
    } else {
      switch (ch) {
      case '.':
        kind = TokenKind::Dot;
        break;
      case '$':
        kind = TokenKind::Dollar;
        break;
      case '[':
        kind = TokenKind::Open;
        break;
      case ']':
        kind = TokenKind::Close;
        break;
      }
    }
    tokens.push_back({kind, begin});
  }

  if (tokens.empty() || tokens.back().kind != TokenKind::Dot)
    return std::nullopt;
  const auto end = tokens.pop_back_val().begin;
  std::size_t index = tokens.size();
  for (;;) {
    while (index && tokens[index - 1].kind == TokenKind::Close) {
      unsigned depth = 1;
      --index;
      while (index && depth) {
        const auto kind = tokens[--index].kind;
        if (kind == TokenKind::Open)
          --depth;
        else if (kind == TokenKind::Close)
          ++depth;
      }
      if (depth)
        return std::nullopt;
    }
    if (!index || tokens[index - 1].kind != TokenKind::Name)
      return std::nullopt;
    --index;
    if (!index || tokens[index - 1].kind != TokenKind::Dot)
      break;
    --index;
  }
  if (index && tokens[index - 1].kind == TokenKind::Dollar)
    --index;
  return prefix.slice(tokens[index].begin, end).rtrim();
}

std::vector<PathSuggestion> path_suggestions(PathRole role, llvm::StringRef atom) {
  const bool quoted = atom.starts_with('\'') || atom.starts_with('"');
  const char quote = quoted ? atom.front() : '\'';
  // Dynamic strings need evaluation, which Tab completion never performs.
  if (quote == '"' && atom.find_first_of("${}") != llvm::StringRef::npos)
    return {};
  std::string prefix;
  try {
    prefix = quoted ? path_prefix(atom, quote) : atom.str();
  } catch (const std::exception &) {
    return {};
  }
  if (prefix == "~" || llvm::StringRef(prefix).starts_with("~/")) {
    llvm::SmallString<128> home;
    if (!llvm::sys::path::home_directory(home))
      return {};
    prefix = home.str().str() + "/" + prefix.substr(std::min<std::size_t>(2, prefix.size()));
  }
  if (prefix.find('\0') != std::string::npos)
    return {};
  const fs::path path(prefix);
  if (role == PathRole::Relative && path.is_absolute())
    return {};
  const auto parent = path.parent_path();
  const auto basename = path.filename().string();
  std::vector<PathSuggestion> choices;
  std::error_code error;
  for (fs::directory_iterator entry(parent.empty() ? fs::path(".") : parent, error),
       end; !error && entry != end; entry.increment(error)) {
    auto name = entry->path().filename().string();
    if (!llvm::StringRef(name).starts_with(basename) || !json::isUTF8(name))
      continue;
    std::error_code issue;
    const auto status = entry->status(issue);
    const bool directory = fs::is_directory(status);
    if (issue || (!directory && (role == PathRole::Directory || !fs::is_regular_file(status))))
      continue;
    if (directory)
      name += '/';
    const auto spelling = (parent / name).string();
    const char delimiter = quote == '"' && llvm::StringRef(spelling).find_first_of("${}") !=
                                               llvm::StringRef::npos ? '\'' : quote;
    choices.push_back({escape_path(name, 0) + (directory ? "  directory" : "  file"),
                       delimiter + escape_path(spelling, delimiter) + delimiter});
  }
  std::sort(choices.begin(), choices.end(), [](const auto &left, const auto &right) {
    return left.display < right.display;
  });
  return choices;
}

llvm::json::Array complete_fields(Values &values, llvm::StringRef reference,
                                  bool presence) {
  if (reference.size() > 8192)
    return {};
  auto syntax = parse_ctk(reference);
  if (!syntax) {
    llvm::consumeError(syntax.takeError());
    return {};
  }
  try {
    const auto *value = resolve(values, *syntax);
    return value ? fields_for(*value, presence) : json::Array{};
  } catch (const std::exception &) {
    // Invalid or incomplete references simply have no completion candidates.
    return {};
  }
}

} // namespace ctk::jit
