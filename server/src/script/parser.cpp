#include "ctk/script/error.hpp"
#include "generated/CtkScriptLexer.h"
#include "generated/CtkScriptParser.h"
#include "program.hpp"
#include "scoped_block.hpp"
#include "syntax_errors.hpp"
#include <cctype>
#include <charconv>
#include <cmath>
#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <limits>
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
    if (auto *target = match->expression()) {
      auto parsed_target = expression(target);
      if (parsed_target->kind == Expression::Kind::Member &&
          parsed_target->name != "inputs" && parsed_target->name != "paths" &&
          parsed_target->name != "length") {
        result->binding = parsed_target->name;
        result->target = parsed_target->source;
      } else {
        result->target = std::move(parsed_target);
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
  } else if (auto *list =
                 dynamic_cast<Parser::ListExpressionContext *>(context)) {
    result->kind = Expression::Kind::List;
    for (auto *child : list->expression())
      result->elements.push_back(expression(child));
  } else if (auto *object =
                 dynamic_cast<Parser::ObjectExpressionContext *>(context)) {
    result->kind = Expression::Kind::Object;
    for (std::size_t i = 0; i < object->expression().size(); ++i) {
      auto *key = object->objectKey(i);
      if (key->Identifier())
        result->keys.push_back(key->Identifier()->getText());
      else if (key->StringLiteral())
        result->keys.push_back(string_literal(key->StringLiteral()->getText()));
      else
        result->keys.push_back(key->getText());
      result->elements.push_back(expression(object->expression(i)));
    }
  } else if (auto *files =
                 dynamic_cast<Parser::FilesExpressionContext *>(context)) {
    result->kind = Expression::Kind::Files;
    result->source = expression(files->expression());
  } else if (auto *loop =
                 dynamic_cast<Parser::ForeachExpressionContext *>(context)) {
    result->kind = Expression::Kind::Foreach;
    result->iteration_name = loop->Identifier()->getText();
    result->source = expression(loop->expression());
    result->batch_body = std::make_shared<ScopedBlock>();
    for (auto *child : loop->statement())
      result->batch_body->statements.push_back(statement(child));
  } else if (auto *group =
                 dynamic_cast<Parser::GroupedExpressionContext *>(context)) {
    result->kind = Expression::Kind::Group;
    result->source = expression(group->expression());
  } else if (auto *member =
                 dynamic_cast<Parser::MemberExpressionContext *>(context)) {
    result->kind = Expression::Kind::Member;
    result->name = member->memberName()->getText();
    result->source = expression(member->expression());
  } else if (auto *index =
                 dynamic_cast<Parser::IndexExpressionContext *>(context)) {
    result->kind = Expression::Kind::Index;
    result->source = expression(index->expression(0));
    result->elements.push_back(expression(index->expression(1)));
  } else if (auto *batch =
                 dynamic_cast<Parser::BatchExpressionContext *>(context)) {
    result->kind = Expression::Kind::Batch;
    result->iteration_name = batch->Identifier()->getText();
    result->source = expression(batch->expression());
    result->option = batch->countValue ? "count" : "size";
    result->count = row_index(
        (batch->countValue ? batch->countValue : batch->sizeValue)->getText());
    if (batch->jobsValue)
      result->jobs = row_index(batch->jobsValue->getText());
    if (batch->memoryValue) {
      auto memory = string_literal(batch->memoryValue->getText());
      std::uint64_t multiplier = 1;
      for (const auto &[suffix, factor] :
           std::vector<std::pair<std::string, std::uint64_t>>{
               {"GiB", 1024ULL * 1024 * 1024},
               {"MiB", 1024ULL * 1024},
               {"KiB", 1024ULL}}) {
        if (memory.ends_with(suffix)) {
          multiplier = factor;
          memory.resize(memory.size() - suffix.size());
          break;
        }
      }
      std::uint64_t amount = 0;
      const auto parsed =
          std::from_chars(memory.data(), memory.data() + memory.size(), amount);
      if (parsed.ec != std::errc{} ||
          parsed.ptr != memory.data() + memory.size() || !amount ||
          amount > std::numeric_limits<std::uint64_t>::max() / multiplier)
        throw Error(Code::InvalidArgument, "invalid batch memory limit");
      result->memory_bytes = amount * multiplier;
    }
    result->continue_on_error =
        batch->batchErrorPolicy() &&
        batch->batchErrorPolicy()->getText() == "continue";
    result->progress =
        batch->progressPolicy() && batch->progressPolicy()->getText() == "on";
    result->batch_body = std::make_shared<ScopedBlock>();
    for (auto *child : batch->statement())
      result->batch_body->statements.push_back(statement(child));
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
  } else if (auto *save =
                 dynamic_cast<Parser::SaveStatementContext *>(context)) {
    result.kind = Statement::Kind::Save;
    result.expression = expression(save->expression(0));
    result.destination = expression(save->expression(1));
    result.option = save->Identifier()->getText();
  } else if (auto *value =
                 dynamic_cast<Parser::ValueStatementContext *>(context)) {
    result.kind = Statement::Kind::Value;
    result.expression = expression(value->expression());
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
