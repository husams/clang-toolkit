
// Generated from CtkScript.g4 by ANTLR 4.13.2

#pragma once

#include "antlr4-runtime.h"

namespace ctk::script::grammar {

class CtkScriptParser : public antlr4::Parser {
public:
  enum {
    T__0 = 1,
    T__1 = 2,
    T__2 = 3,
    T__3 = 4,
    T__4 = 5,
    T__5 = 6,
    T__6 = 7,
    T__7 = 8,
    T__8 = 9,
    T__9 = 10,
    T__10 = 11,
    T__11 = 12,
    T__12 = 13,
    T__13 = 14,
    T__14 = 15,
    T__15 = 16,
    T__16 = 17,
    T__17 = 18,
    T__18 = 19,
    T__19 = 20,
    T__20 = 21,
    T__21 = 22,
    T__22 = 23,
    T__23 = 24,
    T__24 = 25,
    T__25 = 26,
    T__26 = 27,
    T__27 = 28,
    T__28 = 29,
    T__29 = 30,
    T__30 = 31,
    T__31 = 32,
    T__32 = 33,
    T__33 = 34,
    T__34 = 35,
    T__35 = 36,
    T__36 = 37,
    Identifier = 38,
    StringLiteral = 39,
    Number = 40,
    Whitespace = 41,
    Comment = 42
  };

  enum {
    RuleProgram = 0,
    RuleStatement = 1,
    RuleExpression = 2,
    RuleFunctionName = 3,
    RuleBatchErrorPolicy = 4,
    RuleProgressPolicy = 5,
    RuleMatcherExpression = 6,
    RuleMatcherArguments = 7,
    RuleMatcherArgument = 8,
    RuleArguments = 9,
    RuleArgument = 10,
    RuleScalar = 11,
    RuleMemberName = 12,
    RuleObjectKey = 13
  };

  explicit CtkScriptParser(antlr4::TokenStream *input);

  CtkScriptParser(antlr4::TokenStream *input,
                  const antlr4::atn::ParserATNSimulatorOptions &options);

  ~CtkScriptParser() override;

  std::string getGrammarFileName() const override;

  const antlr4::atn::ATN &getATN() const override;

  const std::vector<std::string> &getRuleNames() const override;

  const antlr4::dfa::Vocabulary &getVocabulary() const override;

  antlr4::atn::SerializedATNView getSerializedATN() const override;

  class ProgramContext;
  class StatementContext;
  class ExpressionContext;
  class FunctionNameContext;
  class BatchErrorPolicyContext;
  class ProgressPolicyContext;
  class MatcherExpressionContext;
  class MatcherArgumentsContext;
  class MatcherArgumentContext;
  class ArgumentsContext;
  class ArgumentContext;
  class ScalarContext;
  class MemberNameContext;
  class ObjectKeyContext;

  class ProgramContext : public antlr4::ParserRuleContext {
  public:
    ProgramContext(antlr4::ParserRuleContext *parent, size_t invokingState);
    virtual size_t getRuleIndex() const override;
    antlr4::tree::TerminalNode *EOF();
    std::vector<StatementContext *> statement();
    StatementContext *statement(size_t i);

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  ProgramContext *program();

  class StatementContext : public antlr4::ParserRuleContext {
  public:
    StatementContext(antlr4::ParserRuleContext *parent, size_t invokingState);

    StatementContext() = default;
    void copyFrom(StatementContext *context);
    using antlr4::ParserRuleContext::copyFrom;

    virtual size_t getRuleIndex() const override;
  };

  class EmissionContext : public StatementContext {
  public:
    EmissionContext(StatementContext *ctx);

    ExpressionContext *expression();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class ValueStatementContext : public StatementContext {
  public:
    ValueStatementContext(StatementContext *ctx);

    ExpressionContext *expression();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class AssignmentContext : public StatementContext {
  public:
    AssignmentContext(StatementContext *ctx);

    antlr4::tree::TerminalNode *Identifier();
    ExpressionContext *expression();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class IterationContext : public StatementContext {
  public:
    IterationContext(StatementContext *ctx);

    antlr4::tree::TerminalNode *Identifier();
    ExpressionContext *expression();
    std::vector<StatementContext *> statement();
    StatementContext *statement(size_t i);

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class SaveStatementContext : public StatementContext {
  public:
    SaveStatementContext(StatementContext *ctx);

    std::vector<ExpressionContext *> expression();
    ExpressionContext *expression(size_t i);
    antlr4::tree::TerminalNode *Identifier();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  StatementContext *statement();

  class ExpressionContext : public antlr4::ParserRuleContext {
  public:
    ExpressionContext(antlr4::ParserRuleContext *parent, size_t invokingState);

    ExpressionContext() = default;
    void copyFrom(ExpressionContext *context);
    using antlr4::ParserRuleContext::copyFrom;

    virtual size_t getRuleIndex() const override;
  };

  class MatchExpressionContext : public ExpressionContext {
  public:
    MatchExpressionContext(ExpressionContext *ctx);

    MatcherExpressionContext *matcherExpression();
    ExpressionContext *expression();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class BatchExpressionContext : public ExpressionContext {
  public:
    BatchExpressionContext(ExpressionContext *ctx);

    antlr4::Token *sizeValue = nullptr;
    antlr4::Token *countValue = nullptr;
    antlr4::Token *jobsValue = nullptr;
    antlr4::Token *memoryValue = nullptr;
    antlr4::tree::TerminalNode *Identifier();
    ExpressionContext *expression();
    std::vector<antlr4::tree::TerminalNode *> Number();
    antlr4::tree::TerminalNode *Number(size_t i);
    BatchErrorPolicyContext *batchErrorPolicy();
    ProgressPolicyContext *progressPolicy();
    std::vector<StatementContext *> statement();
    StatementContext *statement(size_t i);
    antlr4::tree::TerminalNode *StringLiteral();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class ReferenceExpressionContext : public ExpressionContext {
  public:
    ReferenceExpressionContext(ExpressionContext *ctx);

    antlr4::tree::TerminalNode *Identifier();
    antlr4::tree::TerminalNode *Number();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class FilesExpressionContext : public ExpressionContext {
  public:
    FilesExpressionContext(ExpressionContext *ctx);

    ExpressionContext *expression();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class MemberExpressionContext : public ExpressionContext {
  public:
    MemberExpressionContext(ExpressionContext *ctx);

    ExpressionContext *expression();
    MemberNameContext *memberName();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class GroupedExpressionContext : public ExpressionContext {
  public:
    GroupedExpressionContext(ExpressionContext *ctx);

    ExpressionContext *expression();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class ObjectExpressionContext : public ExpressionContext {
  public:
    ObjectExpressionContext(ExpressionContext *ctx);

    std::vector<ObjectKeyContext *> objectKey();
    ObjectKeyContext *objectKey(size_t i);
    std::vector<ExpressionContext *> expression();
    ExpressionContext *expression(size_t i);

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class ForeachExpressionContext : public ExpressionContext {
  public:
    ForeachExpressionContext(ExpressionContext *ctx);

    antlr4::tree::TerminalNode *Identifier();
    ExpressionContext *expression();
    std::vector<StatementContext *> statement();
    StatementContext *statement(size_t i);

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class CallExpressionContext : public ExpressionContext {
  public:
    CallExpressionContext(ExpressionContext *ctx);

    FunctionNameContext *functionName();
    ArgumentsContext *arguments();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class IndexExpressionContext : public ExpressionContext {
  public:
    IndexExpressionContext(ExpressionContext *ctx);

    std::vector<ExpressionContext *> expression();
    ExpressionContext *expression(size_t i);

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class LiteralExpressionContext : public ExpressionContext {
  public:
    LiteralExpressionContext(ExpressionContext *ctx);

    ScalarContext *scalar();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class ListExpressionContext : public ExpressionContext {
  public:
    ListExpressionContext(ExpressionContext *ctx);

    std::vector<ExpressionContext *> expression();
    ExpressionContext *expression(size_t i);

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class ParseExpressionContext : public ExpressionContext {
  public:
    ParseExpressionContext(ExpressionContext *ctx);

    antlr4::tree::TerminalNode *StringLiteral();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class ScopedExpressionContext : public ExpressionContext {
  public:
    ScopedExpressionContext(ExpressionContext *ctx);

    std::vector<ExpressionContext *> expression();
    ExpressionContext *expression(size_t i);
    std::vector<StatementContext *> statement();
    StatementContext *statement(size_t i);

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  ExpressionContext *expression();
  ExpressionContext *expression(int precedence);
  class FunctionNameContext : public antlr4::ParserRuleContext {
  public:
    FunctionNameContext(antlr4::ParserRuleContext *parent,
                        size_t invokingState);
    virtual size_t getRuleIndex() const override;
    antlr4::tree::TerminalNode *Identifier();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  FunctionNameContext *functionName();

  class BatchErrorPolicyContext : public antlr4::ParserRuleContext {
  public:
    BatchErrorPolicyContext(antlr4::ParserRuleContext *parent,
                            size_t invokingState);
    virtual size_t getRuleIndex() const override;

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  BatchErrorPolicyContext *batchErrorPolicy();

  class ProgressPolicyContext : public antlr4::ParserRuleContext {
  public:
    ProgressPolicyContext(antlr4::ParserRuleContext *parent,
                          size_t invokingState);
    virtual size_t getRuleIndex() const override;

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  ProgressPolicyContext *progressPolicy();

  class MatcherExpressionContext : public antlr4::ParserRuleContext {
  public:
    MatcherExpressionContext(antlr4::ParserRuleContext *parent,
                             size_t invokingState);
    virtual size_t getRuleIndex() const override;
    std::vector<antlr4::tree::TerminalNode *> Identifier();
    antlr4::tree::TerminalNode *Identifier(size_t i);
    std::vector<MatcherArgumentsContext *> matcherArguments();
    MatcherArgumentsContext *matcherArguments(size_t i);

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  MatcherExpressionContext *matcherExpression();

  class MatcherArgumentsContext : public antlr4::ParserRuleContext {
  public:
    MatcherArgumentsContext(antlr4::ParserRuleContext *parent,
                            size_t invokingState);
    virtual size_t getRuleIndex() const override;
    std::vector<MatcherArgumentContext *> matcherArgument();
    MatcherArgumentContext *matcherArgument(size_t i);

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  MatcherArgumentsContext *matcherArguments();

  class MatcherArgumentContext : public antlr4::ParserRuleContext {
  public:
    MatcherArgumentContext(antlr4::ParserRuleContext *parent,
                           size_t invokingState);
    virtual size_t getRuleIndex() const override;
    MatcherExpressionContext *matcherExpression();
    ScalarContext *scalar();
    antlr4::tree::TerminalNode *Identifier();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  MatcherArgumentContext *matcherArgument();

  class ArgumentsContext : public antlr4::ParserRuleContext {
  public:
    ArgumentsContext(antlr4::ParserRuleContext *parent, size_t invokingState);
    virtual size_t getRuleIndex() const override;
    std::vector<ArgumentContext *> argument();
    ArgumentContext *argument(size_t i);

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  ArgumentsContext *arguments();

  class ArgumentContext : public antlr4::ParserRuleContext {
  public:
    ArgumentContext(antlr4::ParserRuleContext *parent, size_t invokingState);

    ArgumentContext() = default;
    void copyFrom(ArgumentContext *context);
    using antlr4::ParserRuleContext::copyFrom;

    virtual size_t getRuleIndex() const override;
  };

  class PositionalArgumentContext : public ArgumentContext {
  public:
    PositionalArgumentContext(ArgumentContext *ctx);

    ExpressionContext *expression();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  class NamedArgumentContext : public ArgumentContext {
  public:
    NamedArgumentContext(ArgumentContext *ctx);

    antlr4::tree::TerminalNode *Identifier();
    ExpressionContext *expression();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  ArgumentContext *argument();

  class ScalarContext : public antlr4::ParserRuleContext {
  public:
    ScalarContext(antlr4::ParserRuleContext *parent, size_t invokingState);
    virtual size_t getRuleIndex() const override;
    antlr4::tree::TerminalNode *StringLiteral();
    antlr4::tree::TerminalNode *Number();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  ScalarContext *scalar();

  class MemberNameContext : public antlr4::ParserRuleContext {
  public:
    MemberNameContext(antlr4::ParserRuleContext *parent, size_t invokingState);
    virtual size_t getRuleIndex() const override;
    antlr4::tree::TerminalNode *Identifier();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  MemberNameContext *memberName();

  class ObjectKeyContext : public antlr4::ParserRuleContext {
  public:
    ObjectKeyContext(antlr4::ParserRuleContext *parent, size_t invokingState);
    virtual size_t getRuleIndex() const override;
    antlr4::tree::TerminalNode *Identifier();
    antlr4::tree::TerminalNode *StringLiteral();

    virtual std::any accept(antlr4::tree::ParseTreeVisitor *visitor) override;
  };

  ObjectKeyContext *objectKey();

  bool sempred(antlr4::RuleContext *_localctx, size_t ruleIndex,
               size_t predicateIndex) override;

  bool expressionSempred(ExpressionContext *_localctx, size_t predicateIndex);

  // By default the static state used to implement the parser is lazily
  // initialized during the first call to the constructor. You can call this
  // function if you wish to initialize the static state ahead of time.
  static void initialize();

private:
};

} // namespace ctk::script::grammar
