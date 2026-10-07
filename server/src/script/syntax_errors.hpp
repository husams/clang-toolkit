#pragma once
#include "antlr4-runtime.h"
namespace ctk::script::detail {
class SyntaxErrors final : public antlr4::BaseErrorListener {
public:
  std::string message;
  void syntaxError(antlr4::Recognizer *, antlr4::Token *, std::size_t line,
                   std::size_t column, const std::string &text,
                   std::exception_ptr) override {
    if (message.empty())
      message = "script line " + std::to_string(line) + ":" +
                std::to_string(column + 1) + ": " + text;
  }
};
} // namespace ctk::script::detail
