#pragma once

#include "grammar/help.hpp"

#include <algorithm>
#include <optional>
#include <vector>

#include <ftxui/dom/elements.hpp>
#include <ftxui/screen/string.hpp>
#include <llvm/ADT/StringRef.h>
#include <llvm/Support/FormatVariadic.h>

namespace ctk::jit::workspace_display {

namespace tui = ftxui;

struct Line {
  std::size_t begin;
  std::size_t end;
  unsigned number;
};

inline std::size_t glyph_end(llvm::StringRef text, std::size_t start) {
  auto end = start + 1;
  while (end < text.size() &&
         (static_cast<unsigned char>(text[end]) & 0xc0) == 0x80)
    ++end;
  return end;
}

inline int glyph_width(llvm::StringRef text) {
  return text == "\t" ? 4 : tui::string_width(text);
}

inline std::vector<Line> lines(llvm::StringRef text, int width, bool wrap) {
  std::vector<Line> result;
  std::size_t start = 0;
  unsigned logical = 1;
  unsigned number = logical;
  int cells = 0;
  for (std::size_t at = 0; at < text.size();) {
    if (text[at] == '\n') {
      result.push_back({start, at, number});
      start = ++at;
      number = ++logical;
      cells = 0;
      continue;
    }
    const auto end = glyph_end(text, at);
    const auto next = glyph_width(text.slice(at, end));
    if (wrap && cells > 0 && cells + next > width) {
      result.push_back({start, at, number});
      start = at;
      number = 0;
      cells = 0;
    }
    cells += next;
    at = end;
  }
  result.push_back({start, text.size(), number});
  return result;
}

inline std::size_t offset_at(llvm::StringRef text, Line line, int cell) {
  auto at = line.begin;
  while (at < line.end && cell > 0) {
    const auto end = glyph_end(text, at);
    cell -= glyph_width(text.slice(at, end));
    if (cell < 0)
      break;
    at = end;
  }
  return at;
}

enum class Role {
  Plain,
  Keyword,
  Reference,
  String,
  Number,
  Comment,
  Operator,
  Node,
  Predicate,
  Traversal,
  Function
};

struct Token {
  std::size_t begin;
  std::size_t end;
  Role role;
  bool open_literal = false;
};

inline bool identifier(char ch) {
  return (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
         (ch >= '0' && ch <= '9') || ch == '_';
}

inline std::vector<Token> tokens(llvm::StringRef text) {
  std::vector<Token> result;
  for (std::size_t at = 0; at < text.size();) {
    const auto start = at;
    const auto ch = text[at++];
    auto role = Role::Plain;
    bool open = false;
    if (ch == '#' || (ch == '/' && at < text.size() && text[at] == '/')) {
      at = text.find('\n', at);
      if (at == llvm::StringRef::npos)
        at = text.size();
      role = Role::Comment;
    } else if (ch == '\'' || ch == '"' || ch == 96) {
      role = Role::String;
      open = true;
      while (at < text.size()) {
        const auto next = text[at++];
        if (next == ch) {
          open = false;
          break;
        }
        if (next == '\\' && at < text.size())
          ++at;
      }
    } else if (identifier(ch) || ch == '$') {
      while (at < text.size() && identifier(text[at]))
        ++at;
      const auto word = text.slice(start, at);
      if ((ch >= '0' && ch <= '9') || word == "true" || word == "false" ||
          word == "null") {
        role = Role::Number;
      } else if (ch == '$') {
        role = Role::Reference;
      } else if (editor_keyword(word)) {
        role = Role::Keyword;
      } else if (text.drop_front(at).ltrim().starts_with("(")) {
        const auto kind = editor_matcher_kind(word);
        role = kind == "node"        ? Role::Node
               : kind == "narrowing" ? Role::Predicate
               : !kind.empty()       ? Role::Traversal
                                     : Role::Function;
      } else {
        role = Role::Reference;
      }
    } else if (llvm::StringRef("+-*/%=<>!|?").contains(ch)) {
      role = Role::Operator;
    } else if (static_cast<unsigned char>(ch) >= 0x80) {
      at = glyph_end(text, start);
    }
    result.push_back({start, at, role, open});
  }
  return result;
}

inline tui::Color color(Role role) {
  switch (role) {
  case Role::Keyword:
    return tui::Color::LightPink1;
  case Role::Reference:
    return tui::Color::MediumTurquoise;
  case Role::String:
    return tui::Color::LightGoldenrod2;
  case Role::Number:
    return tui::Color::Orange1;
  case Role::Comment:
    return tui::Color::Grey50;
  case Role::Operator:
    return tui::Color::Grey82;
  case Role::Node:
    return tui::Color::SkyBlue1;
  case Role::Predicate:
    return tui::Color::LightGreen;
  case Role::Traversal:
    return tui::Color::MediumPurple1;
  case Role::Function:
    return tui::Color::CyanLight;
  case Role::Plain:
    return tui::Color::Grey70;
  }
  return tui::Color::Default;
}

inline tui::Element script_line(llvm::StringRef text, Line line,
                                const std::vector<Token> &tokens,
                                std::optional<std::size_t> cursor = {},
                                tui::Box *cursor_box = nullptr) {
  auto number = line.number ? llvm::formatv("{0,4} │ ", line.number).str()
                            : std::string("     │ ");
  tui::Elements content{tui::text(std::move(number)) | tui::dim};
  const auto part = [&](std::size_t begin, std::size_t end, Role role) {
    if (end <= begin)
      return tui::text("");
    auto value = text.slice(begin, end).str();
    for (std::size_t at = 0; (at = value.find('\t', at)) != std::string::npos;
         at += 4)
      value.replace(at, 1, "    ");
    return tui::text(std::move(value)) | tui::color(color(role));
  };
  auto first = std::lower_bound(
      tokens.begin(), tokens.end(), line.begin,
      [](const Token &token, std::size_t begin) { return token.end <= begin; });
  for (auto item = first; item != tokens.end() && item->begin < line.end;
       ++item) {
    const auto begin = std::max(line.begin, item->begin);
    const auto end = std::min(line.end, item->end);
    if (cursor && begin <= *cursor && *cursor < end) {
      const auto next = std::min(end, glyph_end(text, *cursor));
      content.push_back(part(begin, *cursor, item->role));
      content.push_back(part(*cursor, next, item->role) |
                        tui::focusCursorBar |
                        tui::reflect(*cursor_box));
      content.push_back(part(next, end, item->role));
    } else {
      content.push_back(part(begin, end, item->role));
    }
  }
  if (cursor && *cursor == line.end)
    content.push_back(tui::text(" ") | tui::focusCursorBar |
                      tui::reflect(*cursor_box));
  return tui::hbox(std::move(content));
}

} // namespace ctk::jit::workspace_display
