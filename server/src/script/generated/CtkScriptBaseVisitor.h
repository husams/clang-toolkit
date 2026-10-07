
// Generated from CtkScript.g4 by ANTLR 4.13.2

#pragma once


#include "antlr4-runtime.h"
#include "CtkScriptVisitor.h"


namespace ctk::script::grammar {

/**
 * This class provides an empty implementation of CtkScriptVisitor, which can be
 * extended to create a visitor which only needs to handle a subset of the available methods.
 */
class  CtkScriptBaseVisitor : public CtkScriptVisitor {
public:

  virtual std::any visitProgram(CtkScriptParser::ProgramContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitAssignment(CtkScriptParser::AssignmentContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitEmission(CtkScriptParser::EmissionContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitIteration(CtkScriptParser::IterationContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitLiteralExpression(CtkScriptParser::LiteralExpressionContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitReferenceExpression(CtkScriptParser::ReferenceExpressionContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitCallExpression(CtkScriptParser::CallExpressionContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitParseExpression(CtkScriptParser::ParseExpressionContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitMatchExpression(CtkScriptParser::MatchExpressionContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitScopedExpression(CtkScriptParser::ScopedExpressionContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitFunctionName(CtkScriptParser::FunctionNameContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitMatchTarget(CtkScriptParser::MatchTargetContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitMatcherExpression(CtkScriptParser::MatcherExpressionContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitMatcherArguments(CtkScriptParser::MatcherArgumentsContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitMatcherArgument(CtkScriptParser::MatcherArgumentContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitArguments(CtkScriptParser::ArgumentsContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitNamedArgument(CtkScriptParser::NamedArgumentContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitPositionalArgument(CtkScriptParser::PositionalArgumentContext *ctx) override {
    return visitChildren(ctx);
  }

  virtual std::any visitScalar(CtkScriptParser::ScalarContext *ctx) override {
    return visitChildren(ctx);
  }


};

}  // namespace ctk::script::grammar
