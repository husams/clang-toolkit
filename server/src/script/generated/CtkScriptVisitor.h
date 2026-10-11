
// Generated from CtkScript.g4 by ANTLR 4.13.2

#pragma once

#include "CtkScriptParser.h"
#include "antlr4-runtime.h"

namespace ctk::script::grammar {

/**
 * This class defines an abstract visitor for a parse tree
 * produced by CtkScriptParser.
 */
class CtkScriptVisitor : public antlr4::tree::AbstractParseTreeVisitor {
public:
  /**
   * Visit parse trees produced by CtkScriptParser.
   */
  virtual std::any visitProgram(CtkScriptParser::ProgramContext *context) = 0;

  virtual std::any
  visitAssignment(CtkScriptParser::AssignmentContext *context) = 0;

  virtual std::any visitEmission(CtkScriptParser::EmissionContext *context) = 0;

  virtual std::any
  visitSaveStatement(CtkScriptParser::SaveStatementContext *context) = 0;

  virtual std::any
  visitValueStatement(CtkScriptParser::ValueStatementContext *context) = 0;

  virtual std::any
  visitIteration(CtkScriptParser::IterationContext *context) = 0;

  virtual std::any
  visitMatchExpression(CtkScriptParser::MatchExpressionContext *context) = 0;

  virtual std::any
  visitBatchExpression(CtkScriptParser::BatchExpressionContext *context) = 0;

  virtual std::any visitReferenceExpression(
      CtkScriptParser::ReferenceExpressionContext *context) = 0;

  virtual std::any
  visitFilesExpression(CtkScriptParser::FilesExpressionContext *context) = 0;

  virtual std::any
  visitMemberExpression(CtkScriptParser::MemberExpressionContext *context) = 0;

  virtual std::any visitGroupedExpression(
      CtkScriptParser::GroupedExpressionContext *context) = 0;

  virtual std::any
  visitObjectExpression(CtkScriptParser::ObjectExpressionContext *context) = 0;

  virtual std::any visitForeachExpression(
      CtkScriptParser::ForeachExpressionContext *context) = 0;

  virtual std::any
  visitCallExpression(CtkScriptParser::CallExpressionContext *context) = 0;

  virtual std::any
  visitIndexExpression(CtkScriptParser::IndexExpressionContext *context) = 0;

  virtual std::any visitLiteralExpression(
      CtkScriptParser::LiteralExpressionContext *context) = 0;

  virtual std::any
  visitListExpression(CtkScriptParser::ListExpressionContext *context) = 0;

  virtual std::any
  visitParseExpression(CtkScriptParser::ParseExpressionContext *context) = 0;

  virtual std::any
  visitScopedExpression(CtkScriptParser::ScopedExpressionContext *context) = 0;

  virtual std::any
  visitFunctionName(CtkScriptParser::FunctionNameContext *context) = 0;

  virtual std::any
  visitBatchErrorPolicy(CtkScriptParser::BatchErrorPolicyContext *context) = 0;

  virtual std::any
  visitProgressPolicy(CtkScriptParser::ProgressPolicyContext *context) = 0;

  virtual std::any visitMatcherExpression(
      CtkScriptParser::MatcherExpressionContext *context) = 0;

  virtual std::any
  visitMatcherArguments(CtkScriptParser::MatcherArgumentsContext *context) = 0;

  virtual std::any
  visitMatcherArgument(CtkScriptParser::MatcherArgumentContext *context) = 0;

  virtual std::any
  visitArguments(CtkScriptParser::ArgumentsContext *context) = 0;

  virtual std::any
  visitNamedArgument(CtkScriptParser::NamedArgumentContext *context) = 0;

  virtual std::any visitPositionalArgument(
      CtkScriptParser::PositionalArgumentContext *context) = 0;

  virtual std::any visitScalar(CtkScriptParser::ScalarContext *context) = 0;

  virtual std::any
  visitMemberName(CtkScriptParser::MemberNameContext *context) = 0;

  virtual std::any
  visitObjectKey(CtkScriptParser::ObjectKeyContext *context) = 0;
};

} // namespace ctk::script::grammar
