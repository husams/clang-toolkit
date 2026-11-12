#include "syntax.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <iterator>
#include <limits>
#include <memory>
#include <optional>
#include <ranges>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>

#define PCRE2_CODE_UNIT_WIDTH 8
#include <pcre2.h>

#include <llvm/ADT/Hashing.h>
#include <llvm/Support/FormatVariadic.h>
#include <llvm/Support/JSON.h>

namespace ctk::jit {
namespace {

using Symbol = unsigned;

enum class ChildMode : std::uint8_t { Keep, Discard, Splice };

struct Terminal {
  const char *name;
  std::string_view pattern;
  int priority;
};

struct Rhs {
  Symbol symbol;
  ChildMode mode;
};

struct Rule {
  Symbol lhs;
  const char *name;
  unsigned offset;
  unsigned length;
  unsigned order;
  int priority;
  bool inline_single;

  const Rhs &operator[](unsigned i) const;
};

#include "tables.inc"

const Rhs &Rule::operator[](unsigned i) const { return expansions[offset + i]; }

constexpr bool terminal(Symbol symbol) { return symbol < std::size(terminals); }

using Regex = std::unique_ptr<pcre2_code, decltype(&pcre2_code_free)>;
using MatchData =
    std::unique_ptr<pcre2_match_data, decltype(&pcre2_match_data_free)>;

Regex compile_regex(const Terminal &term) {
  int error = 0;
  PCRE2_SIZE offset = 0;
  auto *result = pcre2_compile(
      reinterpret_cast<PCRE2_SPTR>(term.pattern.data()), term.pattern.size(),
      PCRE2_UTF | PCRE2_UCP | PCRE2_ANCHORED, &error, &offset, nullptr);
  if (!result) {
    std::array<PCRE2_UCHAR, 256> message{};
    pcre2_get_error_message(error, message.data(), message.size());
    throw std::runtime_error(
        llvm::formatv("CTK grammar terminal {0}, offset {1}: {2}", term.name,
                      offset, reinterpret_cast<const char *>(message.data()))
            .str());
  }
  return Regex(result, &pcre2_code_free);
}

struct Grammar {
  std::array<std::vector<unsigned>, symbol_count> productions;
  std::vector<Regex> regex;

  Grammar() {
    for (unsigned i = 0; i < std::size(rules); ++i)
      productions[rules[i].lhs].push_back(i);
    regex.reserve(std::size(terminals));
    for (const auto &term : terminals)
      regex.push_back(compile_regex(term));
  }
};

const Grammar &grammar() {
  static const Grammar value;
  return value;
}

constexpr bool continuation_byte(char byte) {
  return (static_cast<unsigned char>(byte) & 0xc0) == 0x80;
}

using NodeId = std::size_t;
constexpr NodeId no_node = std::numeric_limits<NodeId>::max();

struct Alternative {
  NodeId left;
  NodeId right;
  unsigned order = 0;
  int priority = 0;

  bool operator==(const Alternative &) const = default;
};

struct ForestNode {
  enum class Type : std::uint8_t { Prefix, Symbol, Token };
  Type type;
  unsigned name;
  std::size_t begin;
  std::size_t end;
  std::vector<Alternative> alternatives;
  std::optional<std::int64_t> score;
  std::size_t choice = 0;
  bool visiting = false;
};

struct Item {
  unsigned rule;
  unsigned dot;
  std::size_t begin;

  bool operator==(const Item &) const = default;
};

struct ItemHash {
  std::size_t operator()(const Item &item) const {
    return llvm::hash_combine(item.rule, item.dot, item.begin);
  }
};

struct Completed {
  Symbol symbol;
  std::size_t begin;

  bool operator==(const Completed &) const = default;
};

struct CompletedHash {
  std::size_t operator()(const Completed &symbol) const {
    return llvm::hash_combine(symbol.symbol, symbol.begin);
  }
};

struct State {
  Item item;
  NodeId prefix;
};

struct Column {
  std::vector<State> items;
  std::unordered_map<Item, NodeId, ItemHash> prefixes;
  std::unordered_map<Completed, NodeId, CompletedHash> completed;
  std::unordered_map<Symbol, std::vector<State>> waiters;
  std::unordered_map<Symbol, std::vector<NodeId>> scanned;
};

class Parser {
public:
  explicit Parser(llvm::StringRef source)
      : source(source), ruleset(grammar()),
        matches(pcre2_match_data_create(1, nullptr), &pcre2_match_data_free),
        columns(source.size() + 1) {
    if (!matches)
      throw std::bad_alloc();
  }

  llvm::Expected<Syntax> parse() {
    start();

    std::optional<Syntax> result;
    std::optional<std::int64_t> best;
    for (std::size_t end = 0; end <= source.size(); ++end) {
      advance_column(end);
      const auto &column = columns[end];
      const auto root = column.completed.find({start_symbol, 0});
      if (root == column.completed.end() || !trailing_trivia(end))
        continue;
      const auto score = resolve(root->second);
      if (score && (!best || *score >= *best)) {
        result = tree(root->second);
        best = score;
      }
    }
    if (!result)
      return diagnostic();
    return std::move(*result);
  }

  PathRole path_role_at(std::size_t offset) {
    start();
    for (std::size_t end = 0; end <= offset; ++end)
      advance_column(end);
    auto role = PathRole::None;
    for (const auto &[symbol, tokens] : columns[offset].scanned) {
      if (tokens.empty())
        continue;
      const std::string_view name = terminals[symbol].name;
      if (name == "LEGACY_DIRECTORY_STRING")
        return PathRole::Directory;
      if (name == "LEGACY_PATH_STRING")
        role = PathRole::Relative;
      else if (name == "LEGACY_FILE_STRING" && role == PathRole::None)
        role = PathRole::File;
    }
    return role;
  }

private:
  void start() {
    for (const auto rule : ruleset.productions[start_symbol])
      add(0, {rule, 0, 0});
  }

  void advance_column(std::size_t end) {
    auto &items = columns[end].items;
    for (std::size_t i = 0; i < items.size(); ++i)
      process(end, items[i]);
  }

  NodeId make_node(ForestNode::Type type, unsigned name, std::size_t begin,
                   std::size_t end) {
    nodes.push_back({type, name, begin, end, {}, std::nullopt, 0, false});
    return nodes.size() - 1;
  }

  void append(NodeId node, Alternative alternative) {
    auto &alternatives = nodes[node].alternatives;
    if (std::ranges::find(alternatives, alternative) == alternatives.end())
      alternatives.push_back(alternative);
  }

  void add(std::size_t end, Item item, NodeId previous = no_node,
           NodeId child = no_node) {
    auto &column = columns[end];
    const auto [position, fresh] = column.prefixes.try_emplace(item, no_node);
    if (fresh) {
      position->second =
          make_node(ForestNode::Type::Prefix, item.rule, item.begin, end);
      column.items.push_back({item, position->second});
    }
    append(position->second, {previous, child});
  }

  void advance(State state, NodeId child, std::size_t end) {
    const auto item = state.item;
    add(end, {item.rule, item.dot + 1, item.begin}, state.prefix, child);
  }

  void process(std::size_t end, State state) {
    const auto item = state.item;
    const auto &rule = rules[item.rule];
    if (item.dot == rule.length) {
      complete(end, state, rule);
      return;
    }

    const auto symbol = rule[item.dot].symbol;
    if (terminal(symbol)) {
      for (const auto child : scan(symbol, end))
        advance(state, child, nodes[child].end);
      return;
    }

    auto &column = columns[end];
    auto &waiters = column.waiters[symbol];
    const bool first = waiters.empty();
    waiters.push_back(state);
    if (first)
      for (const auto production : ruleset.productions[symbol])
        add(end, {production, 0, end});

    if (const auto ready = column.completed.find({symbol, end});
        ready != column.completed.end())
      advance(state, ready->second, end);
  }

  void complete(std::size_t end, State state, const Rule &rule) {
    const auto [position, fresh] = columns[end].completed.try_emplace(
        {rule.lhs, state.item.begin}, no_node);
    if (fresh)
      position->second =
          make_node(ForestNode::Type::Symbol, rule.lhs, state.item.begin, end);
    const auto symbol = position->second;
    append(symbol, {state.prefix, no_node, rule.order, rule.priority});
    if (!fresh)
      return;

    auto &origin = columns[state.item.begin].waiters;
    if (const auto waiting = origin.find(rule.lhs); waiting != origin.end())
      for (const auto waiter : waiting->second)
        advance(waiter, symbol, end);
  }

  std::optional<std::size_t> match(Symbol symbol, llvm::StringRef input,
                                   std::size_t offset) {
    const auto result = pcre2_match(
        ruleset.regex[symbol].get(), reinterpret_cast<PCRE2_SPTR>(input.data()),
        input.size(), offset, PCRE2_NO_UTF_CHECK, matches.get(), nullptr);
    if (result < 0 && result != PCRE2_ERROR_NOMATCH)
      throw std::runtime_error(llvm::formatv("CTK lexer {0}: regex error {1}",
                                             terminals[symbol].name, result)
                                   .str());
    if (result >= 0)
      return pcre2_get_ovector_pointer(matches.get())[1];
    return std::nullopt;
  }

  const std::vector<NodeId> &scan(Symbol symbol, std::size_t offset) {
    auto &scanned = columns[offset].scanned;
    const auto [entry, fresh] = scanned.try_emplace(symbol);
    auto &results = entry->second;
    if (!fresh)
      return results;

    if (offset < source.size()) {
      if (const auto end = match(symbol, source, offset);
          end && *end > offset) {
        results.push_back(
            make_node(ForestNode::Type::Token, symbol, offset, *end));

        // Lark's dynamic-complete lexer also retries shorter prefixes of the
        // longest match. Retry on an isolated token, which preserves how its
        // lookarounds behave when a shorter token is considered.
        const auto text = source.slice(offset, *end);
        for (std::size_t length = text.size() - 1; length > 0; --length) {
          if (continuation_byte(text[length]))
            continue;
          if (const auto shorter = match(symbol, text.take_front(length), 0);
              shorter && *shorter > 0) {
            const auto shortened_end = offset + *shorter;
            if (nodes[results.back()].end != shortened_end)
              results.push_back(make_node(ForestNode::Type::Token, symbol,
                                          offset, shortened_end));
          }
        }
      }
    }

    for (const auto ignore : ignores) {
      if (const auto end = match(ignore, source, offset);
          end && *end > offset) {
        furthest = std::max(furthest, *end);
        const auto &after = scan(symbol, *end);
        results.insert(results.end(), after.begin(), after.end());
      }
    }
    if (!results.empty())
      furthest = std::max(furthest, nodes[results.front()].end);
    return results;
  }

  bool trailing_trivia(std::size_t offset) {
    while (offset < source.size()) {
      std::size_t next = offset;
      for (const auto ignore : ignores)
        next = std::max(next, match(ignore, source, offset).value_or(offset));
      if (next == offset)
        return false;
      offset = next;
    }
    return true;
  }

  llvm::Error diagnostic() const {
    const auto before = source.take_front(furthest);
    const auto line =
        static_cast<std::size_t>(std::ranges::count(before, '\n')) + 1;
    const auto newline = before.rfind('\n');
    const auto prefix = newline == llvm::StringRef::npos
                            ? before
                            : before.drop_front(newline + 1);
    const auto column =
        std::ranges::count_if(
            prefix, [](char byte) { return !continuation_byte(byte); }) +
        1;
    return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                   "line %zu, column %td: %s", line, column,
                                   furthest == source.size()
                                       ? "incomplete CTK input"
                                       : "unexpected CTK input");
  }

  std::optional<std::int64_t> resolve(NodeId id) {
    if (id == no_node)
      return 0;
    auto &node = nodes[id];
    if (node.type == ForestNode::Type::Token)
      return terminals[node.name].priority;
    if (node.visiting)
      return std::nullopt;
    if (node.score)
      return node.score;
    node.visiting = true;
    for (std::size_t index = 0; index < node.alternatives.size(); ++index) {
      const auto &alternative = node.alternatives[index];
      const auto left = resolve(alternative.left);
      const auto right = resolve(alternative.right);
      if (!left || !right)
        continue;
      const auto score = *left + *right + alternative.priority;
      if (!node.score || score > *node.score ||
          (score == *node.score &&
           alternative.order < node.alternatives[node.choice].order)) {
        node.choice = index;
        node.score = score;
      }
    }
    node.visiting = false;
    return node.score;
  }

  void flatten(NodeId prefix, std::vector<NodeId> &children) const {
    if (prefix == no_node)
      return;
    const auto &item = nodes[prefix];
    const auto &chosen = item.alternatives[item.choice];
    flatten(chosen.left, children);
    if (chosen.right != no_node)
      children.push_back(chosen.right);
  }

  Syntax tree(NodeId id) const {
    const auto &node = nodes[id];
    if (node.type == ForestNode::Type::Token)
      return {terminals[node.name].name,
              source.slice(node.begin, node.end),
              node.begin,
              node.end,
              {}};

    const auto prefix = node.alternatives[node.choice].left;
    const auto &rule = rules[nodes[prefix].name];
    Syntax result{rule.name, {}, node.begin, node.end, {}};
    std::vector<NodeId> children;
    flatten(prefix, children);
    bool has_span = false;
    for (unsigned index = 0; index < children.size(); ++index) {
      auto child = tree(children[index]);
      if (child.end > child.begin) {
        if (!has_span)
          result.begin = child.begin;
        has_span = true;
        result.end = child.end;
      }
      switch (rule[index].mode) {
      case ChildMode::Keep:
        result.children.push_back(std::move(child));
        break;
      case ChildMode::Splice:
        result.children.insert(result.children.end(),
                               std::make_move_iterator(child.children.begin()),
                               std::make_move_iterator(child.children.end()));
        break;
      case ChildMode::Discard:
        break;
      }
    }
    if (rule.inline_single && result.children.size() == 1)
      return std::move(result.children.front());
    return result;
  }

  llvm::StringRef source;
  const Grammar &ruleset;
  MatchData matches;
  std::vector<Column> columns;
  std::vector<ForestNode> nodes;
  std::size_t furthest = 0;
};

} // namespace

namespace {

unsigned from_hex(char digit) {
  if (digit >= '0' && digit <= '9')
    return digit - '0';
  if (digit >= 'a' && digit <= 'f')
    return digit - 'a' + 10;
  if (digit >= 'A' && digit <= 'F')
    return digit - 'A' + 10;
  throw std::runtime_error("invalid hexadecimal escape");
}

void append_utf8(std::string &result, std::uint32_t code) {
  if (code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff))
    throw std::runtime_error("invalid Unicode escape");
  if (code < 0x80) {
    result.push_back(static_cast<char>(code));
    return;
  }
  const auto width = code < 0x800 ? 2 : code < 0x10000 ? 3 : 4;
  std::array<char, 4> bytes{};
  for (int i = width - 1; i > 0; --i) {
    bytes[i] = static_cast<char>(0x80 | (code & 0x3f));
    code >>= 6;
  }
  bytes[0] = static_cast<char>((0xf00 >> width) | code);
  result.append(bytes.data(), width);
}

} // namespace

std::string decode_ctk_string(std::string_view input) {
  if (input.size() < 2 || (input.front() != '\'' && input.front() != '"') ||
      input.back() != input.front())
    throw std::runtime_error("expected a quoted CTK string");
  input.remove_prefix(1);
  input.remove_suffix(1);
  std::string result;
  for (std::size_t i = 0; i < input.size(); ++i) {
    const auto ch = input[i];
    if (ch != '\\') {
      result.push_back(ch);
      continue;
    }
    if (++i == input.size())
      throw std::runtime_error("incomplete string escape");
    switch (const auto escape = input[i]) {
    case '\'':
    case '"':
    case '\\':
      result.push_back(escape);
      break;
    case 'a':
      result.push_back('\a');
      break;
    case 'b':
      result.push_back('\b');
      break;
    case 'f':
      result.push_back('\f');
      break;
    case 'n':
      result.push_back('\n');
      break;
    case 'r':
      result.push_back('\r');
      break;
    case 't':
      result.push_back('\t');
      break;
    case 'v':
      result.push_back('\v');
      break;
    case '\n':
      break;
    case 'x':
    case 'u':
    case 'U': {
      const auto width = escape == 'x' ? 2U : escape == 'u' ? 4U : 8U;
      if (input.size() - i - 1 < width)
        throw std::runtime_error("incomplete hexadecimal escape");
      std::uint32_t code = 0;
      for (unsigned digit = 0; digit < width; ++digit)
        code = (code << 4) | from_hex(input[++i]);
      append_utf8(result, code);
      break;
    }
    default:
      if (escape >= '0' && escape <= '7') {
        unsigned code = escape - '0';
        for (unsigned digit = 1; digit < 3 && i + 1 < input.size() &&
                                 input[i + 1] >= '0' && input[i + 1] <= '7';
             ++digit)
          code = (code << 3) | (input[++i] - '0');
        append_utf8(result, code);
      } else {
        result.push_back('\\');
        result.push_back(escape);
      }
    }
  }
  return result;
}

llvm::Expected<Syntax> parse_ctk(llvm::StringRef source) {
  if (!llvm::json::isUTF8(source))
    return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                   "CTK input must be UTF-8");
  try {
    return Parser(source).parse();
  } catch (const std::exception &error) {
    return llvm::createStringError(llvm::inconvertibleErrorCode(), "%s",
                                   error.what());
  }
}

PathRole path_role_after(llvm::StringRef prefix) {
  if (!llvm::json::isUTF8(prefix))
    return PathRole::None;
  // A literal activates the grammar's lookahead for commands such as files.
  const auto probe = prefix.str() + " \"\"";
  return Parser(probe).path_role_at(prefix.size() + 1);
}

} // namespace ctk::jit
