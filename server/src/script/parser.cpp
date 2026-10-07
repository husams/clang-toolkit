#include "ctk/script/error.hpp"
#include "generated/CtkScriptLexer.h"
#include "generated/CtkScriptParser.h"
#include "program.hpp"
#include "scoped_block.hpp"
#include "syntax_errors.hpp"
#include <charconv>
#include <cmath>
#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
namespace ctk::script::detail {
using Parser = grammar::CtkScriptParser;
using Code = ctk::clang_layer::MatchCode;
static Statement statement(Parser::StatementContext *context);
static std::string string_literal(const std::string &text) {
  google::protobuf::Value value;
  if (!google::protobuf::util::JsonStringToMessage(text, &value).ok())
    throw Error(Code::InvalidArgument, "invalid script string");
  return value.string_value();
}
static std::size_t row_index(const std::string &text) {
  std::size_t index;
  auto parsed = std::from_chars(text.data(), text.data() + text.size(), index);
  if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size())
    throw Error(Code::InvalidArgument,
                "script row index must be a nonnegative integer");
  return index;
}
static std::shared_ptr<Expression>
expression(Parser::ExpressionContext *context) {
  auto result = std::make_shared<Expression>();
  if (auto *literal =
          dynamic_cast<Parser::LiteralExpressionContext *>(context)) {
    auto *scalar = literal->scalar();
    const auto text = scalar->getText();
    if (scalar->StringLiteral()) {
      result->literal.set_text(string_literal(text));
    } else if (scalar->Number()) {
      if (text.find_first_of(".eE") == std::string::npos) {
        std::int64_t value;
        auto parsed =
            std::from_chars(text.data(), text.data() + text.size(), value);
        if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size())
          throw Error(Code::InvalidArgument, "script integer is outside int64");
        result->literal.set_integer(value);
      } else {
        double value;
        auto parsed =
            std::from_chars(text.data(), text.data() + text.size(), value);
        if (parsed.ec != std::errc{} ||
            parsed.ptr != text.data() + text.size() || !std::isfinite(value))
          throw Error(Code::InvalidArgument, "script number must be finite");
        result->literal.set_number(value);
      }
    } else
      result->literal.set_boolean(text == "true");
  } else if (auto *reference =
                 dynamic_cast<Parser::ReferenceExpressionContext *>(context)) {
    result->kind = Expression::Kind::Reference;
    result->name = reference->Identifier()->getText();
    if (reference->Number())
      result->row_index = row_index(reference->Number()->getText());
  } else if (auto *call =
                 dynamic_cast<Parser::CallExpressionContext *>(context)) {
    result->kind = Expression::Kind::Call;
    result->name = call->functionName()->getText();
    if (call->arguments())
      for (auto *argument : call->arguments()->argument()) {
        if (auto *named =
                dynamic_cast<Parser::NamedArgumentContext *>(argument))
          result->arguments.push_back({named->Identifier()->getText(),
                                       expression(named->expression())});
        else
          result->arguments.push_back(
              {{},
               expression(
                   dynamic_cast<Parser::PositionalArgumentContext *>(argument)
                       ->expression())});
      }
  } else if (auto *parsed =
                 dynamic_cast<Parser::ParseExpressionContext *>(context)) {
    result->kind = Expression::Kind::Parse;
    result->name = string_literal(parsed->StringLiteral()->getText());
  } else if (auto *match =
                 dynamic_cast<Parser::MatchExpressionContext *>(context)) {
    result->kind = Expression::Kind::Match;
    auto *matcher = match->matcherExpression();
    result->name = matcher->getStart()->getInputStream()->getText(
        antlr4::misc::Interval(matcher->getStart()->getStartIndex(),
                               matcher->getStop()->getStopIndex()));
    if (auto *target = match->matchTarget()) {
      result->target = std::make_shared<Expression>();
      if (target->StringLiteral())
        result->target->literal.set_text(
            string_literal(target->StringLiteral()->getText()));
      else {
        result->target->kind = Expression::Kind::Reference;
        result->target->name = target->Identifier(0)->getText();
        if (target->Number())
          result->target->row_index = row_index(target->Number()->getText());
        if (target->Identifier().size() == 2)
          result->binding = target->Identifier(1)->getText();
      }
    }
  } else if (auto *scoped =
                 dynamic_cast<Parser::ScopedExpressionContext *>(context)) {
    result->kind = Expression::Kind::Scoped;
    result->block = std::make_shared<ScopedBlock>();
    result->block->target = expression(scoped->expression(0));
    for (auto *child : scoped->statement())
      result->block->statements.push_back(statement(child));
    result->block->yielded = expression(scoped->expression(1));
  }
  return result;
}
static Statement statement(Parser::StatementContext *context) {
  Statement result;
  if (auto *assignment = dynamic_cast<Parser::AssignmentContext *>(context)) {
    result.kind = Statement::Kind::Assignment;
    result.name = assignment->Identifier()->getText();
    result.expression = expression(assignment->expression());
  } else if (auto *emission =
                 dynamic_cast<Parser::EmissionContext *>(context)) {
    result.expression = expression(emission->expression());
  } else if (auto *iteration =
                 dynamic_cast<Parser::IterationContext *>(context)) {
    result.kind = Statement::Kind::Iteration;
    result.name = iteration->Identifier()->getText();
    result.expression = expression(iteration->expression());
    for (auto *child : iteration->statement())
      result.body.push_back(statement(child));
  }
  return result;
}
Program parse(const std::string &source) {
  antlr4::ANTLRInputStream input(source);
  grammar::CtkScriptLexer lexer(&input);
  SyntaxErrors errors;
  lexer.removeErrorListeners();
  lexer.addErrorListener(&errors);
  antlr4::CommonTokenStream tokens(&lexer);
  tokens.fill();
  if (!errors.message.empty())
    throw Error(Code::InvalidArgument, errors.message);
  if (tokens.size() > 100000)
    throw Error(Code::ResourceExhausted, "script token limit exceeded");
  std::size_t depth = 0;
  for (auto *token : tokens.getTokens()) {
    const auto text = token->getText();
    if (text == "(" || text == "{" || text == "[") {
      if (++depth > 64)
        throw Error(Code::ResourceExhausted, "script nesting limit exceeded");
    } else if ((text == ")" || text == "}" || text == "]") && depth)
      --depth;
  }
  Parser parser(&tokens);
  parser.removeErrorListeners();
  parser.addErrorListener(&errors);
  auto *tree = parser.program();
  if (!errors.message.empty())
    throw Error(Code::InvalidArgument, errors.message);
  Program result;
  for (auto *child : tree->statement())
    result.statements.push_back(statement(child));
  return result;
}
} // namespace ctk::script::detail
