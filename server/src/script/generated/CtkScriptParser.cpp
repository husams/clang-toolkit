
// Generated from CtkScript.g4 by ANTLR 4.13.2


#include "CtkScriptVisitor.h"

#include "CtkScriptParser.h"


using namespace antlrcpp;
using namespace ctk::script::grammar;

using namespace antlr4;

namespace {

struct CtkScriptParserStaticData final {
  CtkScriptParserStaticData(std::vector<std::string> ruleNames,
                        std::vector<std::string> literalNames,
                        std::vector<std::string> symbolicNames)
      : ruleNames(std::move(ruleNames)), literalNames(std::move(literalNames)),
        symbolicNames(std::move(symbolicNames)),
        vocabulary(this->literalNames, this->symbolicNames) {}

  CtkScriptParserStaticData(const CtkScriptParserStaticData&) = delete;
  CtkScriptParserStaticData(CtkScriptParserStaticData&&) = delete;
  CtkScriptParserStaticData& operator=(const CtkScriptParserStaticData&) = delete;
  CtkScriptParserStaticData& operator=(CtkScriptParserStaticData&&) = delete;

  std::vector<antlr4::dfa::DFA> decisionToDFA;
  antlr4::atn::PredictionContextCache sharedContextCache;
  const std::vector<std::string> ruleNames;
  const std::vector<std::string> literalNames;
  const std::vector<std::string> symbolicNames;
  const antlr4::dfa::Vocabulary vocabulary;
  antlr4::atn::SerializedATNView serializedATN;
  std::unique_ptr<antlr4::atn::ATN> atn;
};

::antlr4::internal::OnceFlag ctkscriptParserOnceFlag;
#if ANTLR4_USE_THREAD_LOCAL_CACHE
static thread_local
#endif
std::unique_ptr<CtkScriptParserStaticData> ctkscriptParserStaticData = nullptr;

void ctkscriptParserInitialize() {
#if ANTLR4_USE_THREAD_LOCAL_CACHE
  if (ctkscriptParserStaticData != nullptr) {
    return;
  }
#else
  assert(ctkscriptParserStaticData == nullptr);
#endif
  auto staticData = std::make_unique<CtkScriptParserStaticData>(
    std::vector<std::string>{
      "program", "statement", "expression", "functionName", "matchTarget", 
      "matcherExpression", "matcherArguments", "matcherArgument", "arguments", 
      "argument", "scalar"
    },
    std::vector<std::string>{
      "", "'let'", "'='", "';'", "'emit'", "'foreach'", "'in'", "'{'", "'}'", 
      "'$'", "'['", "']'", "'('", "')'", "'parse'", "'match'", "'yield'", 
      "'.'", "','", "'true'", "'false'"
    },
    std::vector<std::string>{
      "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", 
      "", "", "", "", "Identifier", "StringLiteral", "Number", "Whitespace", 
      "Comment"
    }
  );
  static const int32_t serializedATNSegment[] = {
  	4,1,25,160,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,6,2,
  	7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,1,0,5,0,24,8,0,10,0,12,0,27,9,0,1,0,1,
  	0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,5,1,
  	47,8,1,10,1,12,1,50,9,1,1,1,1,1,3,1,54,8,1,1,2,1,2,3,2,58,8,2,1,2,1,2,
  	1,2,1,2,3,2,64,8,2,1,2,1,2,1,2,3,2,69,8,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,
  	1,2,3,2,79,8,2,1,2,1,2,1,2,1,2,5,2,85,8,2,10,2,12,2,88,9,2,1,2,1,2,1,
  	2,1,2,1,2,3,2,95,8,2,1,3,1,3,1,4,1,4,1,4,1,4,1,4,1,4,3,4,105,8,4,1,4,
  	1,4,3,4,109,8,4,3,4,111,8,4,1,5,1,5,1,5,3,5,116,8,5,1,5,1,5,1,5,1,5,1,
  	5,3,5,123,8,5,1,5,5,5,126,8,5,10,5,12,5,129,9,5,1,6,1,6,1,6,5,6,134,8,
  	6,10,6,12,6,137,9,6,1,7,1,7,1,7,3,7,142,8,7,1,8,1,8,1,8,5,8,147,8,8,10,
  	8,12,8,150,9,8,1,9,1,9,1,9,1,9,3,9,156,8,9,1,10,1,10,1,10,0,0,11,0,2,
  	4,6,8,10,12,14,16,18,20,0,2,2,0,15,15,21,21,2,0,19,20,22,23,173,0,25,
  	1,0,0,0,2,53,1,0,0,0,4,94,1,0,0,0,6,96,1,0,0,0,8,110,1,0,0,0,10,112,1,
  	0,0,0,12,130,1,0,0,0,14,141,1,0,0,0,16,143,1,0,0,0,18,155,1,0,0,0,20,
  	157,1,0,0,0,22,24,3,2,1,0,23,22,1,0,0,0,24,27,1,0,0,0,25,23,1,0,0,0,25,
  	26,1,0,0,0,26,28,1,0,0,0,27,25,1,0,0,0,28,29,5,0,0,1,29,1,1,0,0,0,30,
  	31,5,1,0,0,31,32,5,21,0,0,32,33,5,2,0,0,33,34,3,4,2,0,34,35,5,3,0,0,35,
  	54,1,0,0,0,36,37,5,4,0,0,37,38,3,4,2,0,38,39,5,3,0,0,39,54,1,0,0,0,40,
  	41,5,5,0,0,41,42,5,21,0,0,42,43,5,6,0,0,43,44,3,4,2,0,44,48,5,7,0,0,45,
  	47,3,2,1,0,46,45,1,0,0,0,47,50,1,0,0,0,48,46,1,0,0,0,48,49,1,0,0,0,49,
  	51,1,0,0,0,50,48,1,0,0,0,51,52,5,8,0,0,52,54,1,0,0,0,53,30,1,0,0,0,53,
  	36,1,0,0,0,53,40,1,0,0,0,54,3,1,0,0,0,55,95,3,20,10,0,56,58,5,9,0,0,57,
  	56,1,0,0,0,57,58,1,0,0,0,58,59,1,0,0,0,59,63,5,21,0,0,60,61,5,10,0,0,
  	61,62,5,23,0,0,62,64,5,11,0,0,63,60,1,0,0,0,63,64,1,0,0,0,64,95,1,0,0,
  	0,65,66,3,6,3,0,66,68,5,12,0,0,67,69,3,16,8,0,68,67,1,0,0,0,68,69,1,0,
  	0,0,69,70,1,0,0,0,70,71,5,13,0,0,71,95,1,0,0,0,72,73,5,14,0,0,73,95,5,
  	22,0,0,74,75,5,15,0,0,75,78,3,10,5,0,76,77,5,6,0,0,77,79,3,8,4,0,78,76,
  	1,0,0,0,78,79,1,0,0,0,79,95,1,0,0,0,80,81,5,6,0,0,81,82,3,4,2,0,82,86,
  	5,7,0,0,83,85,3,2,1,0,84,83,1,0,0,0,85,88,1,0,0,0,86,84,1,0,0,0,86,87,
  	1,0,0,0,87,89,1,0,0,0,88,86,1,0,0,0,89,90,5,16,0,0,90,91,3,4,2,0,91,92,
  	5,3,0,0,92,93,5,8,0,0,93,95,1,0,0,0,94,55,1,0,0,0,94,57,1,0,0,0,94,65,
  	1,0,0,0,94,72,1,0,0,0,94,74,1,0,0,0,94,80,1,0,0,0,95,5,1,0,0,0,96,97,
  	7,0,0,0,97,7,1,0,0,0,98,111,5,22,0,0,99,100,5,9,0,0,100,104,5,21,0,0,
  	101,102,5,10,0,0,102,103,5,23,0,0,103,105,5,11,0,0,104,101,1,0,0,0,104,
  	105,1,0,0,0,105,108,1,0,0,0,106,107,5,17,0,0,107,109,5,21,0,0,108,106,
  	1,0,0,0,108,109,1,0,0,0,109,111,1,0,0,0,110,98,1,0,0,0,110,99,1,0,0,0,
  	111,9,1,0,0,0,112,113,5,21,0,0,113,115,5,12,0,0,114,116,3,12,6,0,115,
  	114,1,0,0,0,115,116,1,0,0,0,116,117,1,0,0,0,117,127,5,13,0,0,118,119,
  	5,17,0,0,119,120,5,21,0,0,120,122,5,12,0,0,121,123,3,12,6,0,122,121,1,
  	0,0,0,122,123,1,0,0,0,123,124,1,0,0,0,124,126,5,13,0,0,125,118,1,0,0,
  	0,126,129,1,0,0,0,127,125,1,0,0,0,127,128,1,0,0,0,128,11,1,0,0,0,129,
  	127,1,0,0,0,130,135,3,14,7,0,131,132,5,18,0,0,132,134,3,14,7,0,133,131,
  	1,0,0,0,134,137,1,0,0,0,135,133,1,0,0,0,135,136,1,0,0,0,136,13,1,0,0,
  	0,137,135,1,0,0,0,138,142,3,10,5,0,139,142,3,20,10,0,140,142,5,21,0,0,
  	141,138,1,0,0,0,141,139,1,0,0,0,141,140,1,0,0,0,142,15,1,0,0,0,143,148,
  	3,18,9,0,144,145,5,18,0,0,145,147,3,18,9,0,146,144,1,0,0,0,147,150,1,
  	0,0,0,148,146,1,0,0,0,148,149,1,0,0,0,149,17,1,0,0,0,150,148,1,0,0,0,
  	151,152,5,21,0,0,152,153,5,2,0,0,153,156,3,4,2,0,154,156,3,4,2,0,155,
  	151,1,0,0,0,155,154,1,0,0,0,156,19,1,0,0,0,157,158,7,1,0,0,158,21,1,0,
  	0,0,19,25,48,53,57,63,68,78,86,94,104,108,110,115,122,127,135,141,148,
  	155
  };
  staticData->serializedATN = antlr4::atn::SerializedATNView(serializedATNSegment, sizeof(serializedATNSegment) / sizeof(serializedATNSegment[0]));

  antlr4::atn::ATNDeserializer deserializer;
  staticData->atn = deserializer.deserialize(staticData->serializedATN);

  const size_t count = staticData->atn->getNumberOfDecisions();
  staticData->decisionToDFA.reserve(count);
  for (size_t i = 0; i < count; i++) { 
    staticData->decisionToDFA.emplace_back(staticData->atn->getDecisionState(i), i);
  }
  ctkscriptParserStaticData = std::move(staticData);
}

}

CtkScriptParser::CtkScriptParser(TokenStream *input) : CtkScriptParser(input, antlr4::atn::ParserATNSimulatorOptions()) {}

CtkScriptParser::CtkScriptParser(TokenStream *input, const antlr4::atn::ParserATNSimulatorOptions &options) : Parser(input) {
  CtkScriptParser::initialize();
  _interpreter = new atn::ParserATNSimulator(this, *ctkscriptParserStaticData->atn, ctkscriptParserStaticData->decisionToDFA, ctkscriptParserStaticData->sharedContextCache, options);
}

CtkScriptParser::~CtkScriptParser() {
  delete _interpreter;
}

const atn::ATN& CtkScriptParser::getATN() const {
  return *ctkscriptParserStaticData->atn;
}

std::string CtkScriptParser::getGrammarFileName() const {
  return "CtkScript.g4";
}

const std::vector<std::string>& CtkScriptParser::getRuleNames() const {
  return ctkscriptParserStaticData->ruleNames;
}

const dfa::Vocabulary& CtkScriptParser::getVocabulary() const {
  return ctkscriptParserStaticData->vocabulary;
}

antlr4::atn::SerializedATNView CtkScriptParser::getSerializedATN() const {
  return ctkscriptParserStaticData->serializedATN;
}


//----------------- ProgramContext ------------------------------------------------------------------

CtkScriptParser::ProgramContext::ProgramContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

tree::TerminalNode* CtkScriptParser::ProgramContext::EOF() {
  return getToken(CtkScriptParser::EOF, 0);
}

std::vector<CtkScriptParser::StatementContext *> CtkScriptParser::ProgramContext::statement() {
  return getRuleContexts<CtkScriptParser::StatementContext>();
}

CtkScriptParser::StatementContext* CtkScriptParser::ProgramContext::statement(size_t i) {
  return getRuleContext<CtkScriptParser::StatementContext>(i);
}


size_t CtkScriptParser::ProgramContext::getRuleIndex() const {
  return CtkScriptParser::RuleProgram;
}


std::any CtkScriptParser::ProgramContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitProgram(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::ProgramContext* CtkScriptParser::program() {
  ProgramContext *_localctx = _tracker.createInstance<ProgramContext>(_ctx, getState());
  enterRule(_localctx, 0, CtkScriptParser::RuleProgram);
  size_t _la = 0;

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    enterOuterAlt(_localctx, 1);
    setState(25);
    _errHandler->sync(this);
    _la = _input->LA(1);
    while ((((_la & ~ 0x3fULL) == 0) &&
      ((1ULL << _la) & 50) != 0)) {
      setState(22);
      statement();
      setState(27);
      _errHandler->sync(this);
      _la = _input->LA(1);
    }
    setState(28);
    match(CtkScriptParser::EOF);
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- StatementContext ------------------------------------------------------------------

CtkScriptParser::StatementContext::StatementContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}


size_t CtkScriptParser::StatementContext::getRuleIndex() const {
  return CtkScriptParser::RuleStatement;
}

void CtkScriptParser::StatementContext::copyFrom(StatementContext *ctx) {
  ParserRuleContext::copyFrom(ctx);
}

//----------------- EmissionContext ------------------------------------------------------------------

CtkScriptParser::ExpressionContext* CtkScriptParser::EmissionContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::EmissionContext::EmissionContext(StatementContext *ctx) { copyFrom(ctx); }


std::any CtkScriptParser::EmissionContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitEmission(this);
  else
    return visitor->visitChildren(this);
}
//----------------- AssignmentContext ------------------------------------------------------------------

tree::TerminalNode* CtkScriptParser::AssignmentContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

CtkScriptParser::ExpressionContext* CtkScriptParser::AssignmentContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::AssignmentContext::AssignmentContext(StatementContext *ctx) { copyFrom(ctx); }


std::any CtkScriptParser::AssignmentContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitAssignment(this);
  else
    return visitor->visitChildren(this);
}
//----------------- IterationContext ------------------------------------------------------------------

tree::TerminalNode* CtkScriptParser::IterationContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

CtkScriptParser::ExpressionContext* CtkScriptParser::IterationContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

std::vector<CtkScriptParser::StatementContext *> CtkScriptParser::IterationContext::statement() {
  return getRuleContexts<CtkScriptParser::StatementContext>();
}

CtkScriptParser::StatementContext* CtkScriptParser::IterationContext::statement(size_t i) {
  return getRuleContext<CtkScriptParser::StatementContext>(i);
}

CtkScriptParser::IterationContext::IterationContext(StatementContext *ctx) { copyFrom(ctx); }


std::any CtkScriptParser::IterationContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitIteration(this);
  else
    return visitor->visitChildren(this);
}
CtkScriptParser::StatementContext* CtkScriptParser::statement() {
  StatementContext *_localctx = _tracker.createInstance<StatementContext>(_ctx, getState());
  enterRule(_localctx, 2, CtkScriptParser::RuleStatement);
  size_t _la = 0;

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    setState(53);
    _errHandler->sync(this);
    switch (_input->LA(1)) {
      case CtkScriptParser::T__0: {
        _localctx = _tracker.createInstance<CtkScriptParser::AssignmentContext>(_localctx);
        enterOuterAlt(_localctx, 1);
        setState(30);
        match(CtkScriptParser::T__0);
        setState(31);
        match(CtkScriptParser::Identifier);
        setState(32);
        match(CtkScriptParser::T__1);
        setState(33);
        expression();
        setState(34);
        match(CtkScriptParser::T__2);
        break;
      }

      case CtkScriptParser::T__3: {
        _localctx = _tracker.createInstance<CtkScriptParser::EmissionContext>(_localctx);
        enterOuterAlt(_localctx, 2);
        setState(36);
        match(CtkScriptParser::T__3);
        setState(37);
        expression();
        setState(38);
        match(CtkScriptParser::T__2);
        break;
      }

      case CtkScriptParser::T__4: {
        _localctx = _tracker.createInstance<CtkScriptParser::IterationContext>(_localctx);
        enterOuterAlt(_localctx, 3);
        setState(40);
        match(CtkScriptParser::T__4);
        setState(41);
        match(CtkScriptParser::Identifier);
        setState(42);
        match(CtkScriptParser::T__5);
        setState(43);
        expression();
        setState(44);
        match(CtkScriptParser::T__6);
        setState(48);
        _errHandler->sync(this);
        _la = _input->LA(1);
        while ((((_la & ~ 0x3fULL) == 0) &&
          ((1ULL << _la) & 50) != 0)) {
          setState(45);
          statement();
          setState(50);
          _errHandler->sync(this);
          _la = _input->LA(1);
        }
        setState(51);
        match(CtkScriptParser::T__7);
        break;
      }

    default:
      throw NoViableAltException(this);
    }
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- ExpressionContext ------------------------------------------------------------------

CtkScriptParser::ExpressionContext::ExpressionContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}


size_t CtkScriptParser::ExpressionContext::getRuleIndex() const {
  return CtkScriptParser::RuleExpression;
}

void CtkScriptParser::ExpressionContext::copyFrom(ExpressionContext *ctx) {
  ParserRuleContext::copyFrom(ctx);
}

//----------------- MatchExpressionContext ------------------------------------------------------------------

CtkScriptParser::MatcherExpressionContext* CtkScriptParser::MatchExpressionContext::matcherExpression() {
  return getRuleContext<CtkScriptParser::MatcherExpressionContext>(0);
}

CtkScriptParser::MatchTargetContext* CtkScriptParser::MatchExpressionContext::matchTarget() {
  return getRuleContext<CtkScriptParser::MatchTargetContext>(0);
}

CtkScriptParser::MatchExpressionContext::MatchExpressionContext(ExpressionContext *ctx) { copyFrom(ctx); }


std::any CtkScriptParser::MatchExpressionContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitMatchExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- CallExpressionContext ------------------------------------------------------------------

CtkScriptParser::FunctionNameContext* CtkScriptParser::CallExpressionContext::functionName() {
  return getRuleContext<CtkScriptParser::FunctionNameContext>(0);
}

CtkScriptParser::ArgumentsContext* CtkScriptParser::CallExpressionContext::arguments() {
  return getRuleContext<CtkScriptParser::ArgumentsContext>(0);
}

CtkScriptParser::CallExpressionContext::CallExpressionContext(ExpressionContext *ctx) { copyFrom(ctx); }


std::any CtkScriptParser::CallExpressionContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitCallExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- ReferenceExpressionContext ------------------------------------------------------------------

tree::TerminalNode* CtkScriptParser::ReferenceExpressionContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

tree::TerminalNode* CtkScriptParser::ReferenceExpressionContext::Number() {
  return getToken(CtkScriptParser::Number, 0);
}

CtkScriptParser::ReferenceExpressionContext::ReferenceExpressionContext(ExpressionContext *ctx) { copyFrom(ctx); }


std::any CtkScriptParser::ReferenceExpressionContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitReferenceExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- LiteralExpressionContext ------------------------------------------------------------------

CtkScriptParser::ScalarContext* CtkScriptParser::LiteralExpressionContext::scalar() {
  return getRuleContext<CtkScriptParser::ScalarContext>(0);
}

CtkScriptParser::LiteralExpressionContext::LiteralExpressionContext(ExpressionContext *ctx) { copyFrom(ctx); }


std::any CtkScriptParser::LiteralExpressionContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitLiteralExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- ParseExpressionContext ------------------------------------------------------------------

tree::TerminalNode* CtkScriptParser::ParseExpressionContext::StringLiteral() {
  return getToken(CtkScriptParser::StringLiteral, 0);
}

CtkScriptParser::ParseExpressionContext::ParseExpressionContext(ExpressionContext *ctx) { copyFrom(ctx); }


std::any CtkScriptParser::ParseExpressionContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitParseExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- ScopedExpressionContext ------------------------------------------------------------------

std::vector<CtkScriptParser::ExpressionContext *> CtkScriptParser::ScopedExpressionContext::expression() {
  return getRuleContexts<CtkScriptParser::ExpressionContext>();
}

CtkScriptParser::ExpressionContext* CtkScriptParser::ScopedExpressionContext::expression(size_t i) {
  return getRuleContext<CtkScriptParser::ExpressionContext>(i);
}

std::vector<CtkScriptParser::StatementContext *> CtkScriptParser::ScopedExpressionContext::statement() {
  return getRuleContexts<CtkScriptParser::StatementContext>();
}

CtkScriptParser::StatementContext* CtkScriptParser::ScopedExpressionContext::statement(size_t i) {
  return getRuleContext<CtkScriptParser::StatementContext>(i);
}

CtkScriptParser::ScopedExpressionContext::ScopedExpressionContext(ExpressionContext *ctx) { copyFrom(ctx); }


std::any CtkScriptParser::ScopedExpressionContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitScopedExpression(this);
  else
    return visitor->visitChildren(this);
}
CtkScriptParser::ExpressionContext* CtkScriptParser::expression() {
  ExpressionContext *_localctx = _tracker.createInstance<ExpressionContext>(_ctx, getState());
  enterRule(_localctx, 4, CtkScriptParser::RuleExpression);
  size_t _la = 0;

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    setState(94);
    _errHandler->sync(this);
    switch (getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(_input, 8, _ctx)) {
    case 1: {
      _localctx = _tracker.createInstance<CtkScriptParser::LiteralExpressionContext>(_localctx);
      enterOuterAlt(_localctx, 1);
      setState(55);
      scalar();
      break;
    }

    case 2: {
      _localctx = _tracker.createInstance<CtkScriptParser::ReferenceExpressionContext>(_localctx);
      enterOuterAlt(_localctx, 2);
      setState(57);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if (_la == CtkScriptParser::T__8) {
        setState(56);
        match(CtkScriptParser::T__8);
      }
      setState(59);
      match(CtkScriptParser::Identifier);
      setState(63);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if (_la == CtkScriptParser::T__9) {
        setState(60);
        match(CtkScriptParser::T__9);
        setState(61);
        match(CtkScriptParser::Number);
        setState(62);
        match(CtkScriptParser::T__10);
      }
      break;
    }

    case 3: {
      _localctx = _tracker.createInstance<CtkScriptParser::CallExpressionContext>(_localctx);
      enterOuterAlt(_localctx, 3);
      setState(65);
      functionName();
      setState(66);
      match(CtkScriptParser::T__11);
      setState(68);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if ((((_la & ~ 0x3fULL) == 0) &&
        ((1ULL << _la) & 16302656) != 0)) {
        setState(67);
        arguments();
      }
      setState(70);
      match(CtkScriptParser::T__12);
      break;
    }

    case 4: {
      _localctx = _tracker.createInstance<CtkScriptParser::ParseExpressionContext>(_localctx);
      enterOuterAlt(_localctx, 4);
      setState(72);
      match(CtkScriptParser::T__13);
      setState(73);
      match(CtkScriptParser::StringLiteral);
      break;
    }

    case 5: {
      _localctx = _tracker.createInstance<CtkScriptParser::MatchExpressionContext>(_localctx);
      enterOuterAlt(_localctx, 5);
      setState(74);
      match(CtkScriptParser::T__14);
      setState(75);
      matcherExpression();
      setState(78);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if (_la == CtkScriptParser::T__5) {
        setState(76);
        match(CtkScriptParser::T__5);
        setState(77);
        matchTarget();
      }
      break;
    }

    case 6: {
      _localctx = _tracker.createInstance<CtkScriptParser::ScopedExpressionContext>(_localctx);
      enterOuterAlt(_localctx, 6);
      setState(80);
      match(CtkScriptParser::T__5);
      setState(81);
      expression();
      setState(82);
      match(CtkScriptParser::T__6);
      setState(86);
      _errHandler->sync(this);
      _la = _input->LA(1);
      while ((((_la & ~ 0x3fULL) == 0) &&
        ((1ULL << _la) & 50) != 0)) {
        setState(83);
        statement();
        setState(88);
        _errHandler->sync(this);
        _la = _input->LA(1);
      }
      setState(89);
      match(CtkScriptParser::T__15);
      setState(90);
      expression();
      setState(91);
      match(CtkScriptParser::T__2);
      setState(92);
      match(CtkScriptParser::T__7);
      break;
    }

    default:
      break;
    }
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- FunctionNameContext ------------------------------------------------------------------

CtkScriptParser::FunctionNameContext::FunctionNameContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

tree::TerminalNode* CtkScriptParser::FunctionNameContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}


size_t CtkScriptParser::FunctionNameContext::getRuleIndex() const {
  return CtkScriptParser::RuleFunctionName;
}


std::any CtkScriptParser::FunctionNameContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitFunctionName(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::FunctionNameContext* CtkScriptParser::functionName() {
  FunctionNameContext *_localctx = _tracker.createInstance<FunctionNameContext>(_ctx, getState());
  enterRule(_localctx, 6, CtkScriptParser::RuleFunctionName);
  size_t _la = 0;

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    enterOuterAlt(_localctx, 1);
    setState(96);
    _la = _input->LA(1);
    if (!(_la == CtkScriptParser::T__14

    || _la == CtkScriptParser::Identifier)) {
    _errHandler->recoverInline(this);
    }
    else {
      _errHandler->reportMatch(this);
      consume();
    }
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- MatchTargetContext ------------------------------------------------------------------

CtkScriptParser::MatchTargetContext::MatchTargetContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

tree::TerminalNode* CtkScriptParser::MatchTargetContext::StringLiteral() {
  return getToken(CtkScriptParser::StringLiteral, 0);
}

std::vector<tree::TerminalNode *> CtkScriptParser::MatchTargetContext::Identifier() {
  return getTokens(CtkScriptParser::Identifier);
}

tree::TerminalNode* CtkScriptParser::MatchTargetContext::Identifier(size_t i) {
  return getToken(CtkScriptParser::Identifier, i);
}

tree::TerminalNode* CtkScriptParser::MatchTargetContext::Number() {
  return getToken(CtkScriptParser::Number, 0);
}


size_t CtkScriptParser::MatchTargetContext::getRuleIndex() const {
  return CtkScriptParser::RuleMatchTarget;
}


std::any CtkScriptParser::MatchTargetContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitMatchTarget(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::MatchTargetContext* CtkScriptParser::matchTarget() {
  MatchTargetContext *_localctx = _tracker.createInstance<MatchTargetContext>(_ctx, getState());
  enterRule(_localctx, 8, CtkScriptParser::RuleMatchTarget);
  size_t _la = 0;

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    setState(110);
    _errHandler->sync(this);
    switch (_input->LA(1)) {
      case CtkScriptParser::StringLiteral: {
        enterOuterAlt(_localctx, 1);
        setState(98);
        match(CtkScriptParser::StringLiteral);
        break;
      }

      case CtkScriptParser::T__8: {
        enterOuterAlt(_localctx, 2);
        setState(99);
        match(CtkScriptParser::T__8);
        setState(100);
        match(CtkScriptParser::Identifier);
        setState(104);
        _errHandler->sync(this);

        _la = _input->LA(1);
        if (_la == CtkScriptParser::T__9) {
          setState(101);
          match(CtkScriptParser::T__9);
          setState(102);
          match(CtkScriptParser::Number);
          setState(103);
          match(CtkScriptParser::T__10);
        }
        setState(108);
        _errHandler->sync(this);

        _la = _input->LA(1);
        if (_la == CtkScriptParser::T__16) {
          setState(106);
          match(CtkScriptParser::T__16);
          setState(107);
          match(CtkScriptParser::Identifier);
        }
        break;
      }

    default:
      throw NoViableAltException(this);
    }
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- MatcherExpressionContext ------------------------------------------------------------------

CtkScriptParser::MatcherExpressionContext::MatcherExpressionContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

std::vector<tree::TerminalNode *> CtkScriptParser::MatcherExpressionContext::Identifier() {
  return getTokens(CtkScriptParser::Identifier);
}

tree::TerminalNode* CtkScriptParser::MatcherExpressionContext::Identifier(size_t i) {
  return getToken(CtkScriptParser::Identifier, i);
}

std::vector<CtkScriptParser::MatcherArgumentsContext *> CtkScriptParser::MatcherExpressionContext::matcherArguments() {
  return getRuleContexts<CtkScriptParser::MatcherArgumentsContext>();
}

CtkScriptParser::MatcherArgumentsContext* CtkScriptParser::MatcherExpressionContext::matcherArguments(size_t i) {
  return getRuleContext<CtkScriptParser::MatcherArgumentsContext>(i);
}


size_t CtkScriptParser::MatcherExpressionContext::getRuleIndex() const {
  return CtkScriptParser::RuleMatcherExpression;
}


std::any CtkScriptParser::MatcherExpressionContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitMatcherExpression(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::MatcherExpressionContext* CtkScriptParser::matcherExpression() {
  MatcherExpressionContext *_localctx = _tracker.createInstance<MatcherExpressionContext>(_ctx, getState());
  enterRule(_localctx, 10, CtkScriptParser::RuleMatcherExpression);
  size_t _la = 0;

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    enterOuterAlt(_localctx, 1);
    setState(112);
    match(CtkScriptParser::Identifier);
    setState(113);
    match(CtkScriptParser::T__11);
    setState(115);
    _errHandler->sync(this);

    _la = _input->LA(1);
    if ((((_la & ~ 0x3fULL) == 0) &&
      ((1ULL << _la) & 16252928) != 0)) {
      setState(114);
      matcherArguments();
    }
    setState(117);
    match(CtkScriptParser::T__12);
    setState(127);
    _errHandler->sync(this);
    _la = _input->LA(1);
    while (_la == CtkScriptParser::T__16) {
      setState(118);
      match(CtkScriptParser::T__16);
      setState(119);
      match(CtkScriptParser::Identifier);
      setState(120);
      match(CtkScriptParser::T__11);
      setState(122);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if ((((_la & ~ 0x3fULL) == 0) &&
        ((1ULL << _la) & 16252928) != 0)) {
        setState(121);
        matcherArguments();
      }
      setState(124);
      match(CtkScriptParser::T__12);
      setState(129);
      _errHandler->sync(this);
      _la = _input->LA(1);
    }
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- MatcherArgumentsContext ------------------------------------------------------------------

CtkScriptParser::MatcherArgumentsContext::MatcherArgumentsContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

std::vector<CtkScriptParser::MatcherArgumentContext *> CtkScriptParser::MatcherArgumentsContext::matcherArgument() {
  return getRuleContexts<CtkScriptParser::MatcherArgumentContext>();
}

CtkScriptParser::MatcherArgumentContext* CtkScriptParser::MatcherArgumentsContext::matcherArgument(size_t i) {
  return getRuleContext<CtkScriptParser::MatcherArgumentContext>(i);
}


size_t CtkScriptParser::MatcherArgumentsContext::getRuleIndex() const {
  return CtkScriptParser::RuleMatcherArguments;
}


std::any CtkScriptParser::MatcherArgumentsContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitMatcherArguments(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::MatcherArgumentsContext* CtkScriptParser::matcherArguments() {
  MatcherArgumentsContext *_localctx = _tracker.createInstance<MatcherArgumentsContext>(_ctx, getState());
  enterRule(_localctx, 12, CtkScriptParser::RuleMatcherArguments);
  size_t _la = 0;

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    enterOuterAlt(_localctx, 1);
    setState(130);
    matcherArgument();
    setState(135);
    _errHandler->sync(this);
    _la = _input->LA(1);
    while (_la == CtkScriptParser::T__17) {
      setState(131);
      match(CtkScriptParser::T__17);
      setState(132);
      matcherArgument();
      setState(137);
      _errHandler->sync(this);
      _la = _input->LA(1);
    }
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- MatcherArgumentContext ------------------------------------------------------------------

CtkScriptParser::MatcherArgumentContext::MatcherArgumentContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

CtkScriptParser::MatcherExpressionContext* CtkScriptParser::MatcherArgumentContext::matcherExpression() {
  return getRuleContext<CtkScriptParser::MatcherExpressionContext>(0);
}

CtkScriptParser::ScalarContext* CtkScriptParser::MatcherArgumentContext::scalar() {
  return getRuleContext<CtkScriptParser::ScalarContext>(0);
}

tree::TerminalNode* CtkScriptParser::MatcherArgumentContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}


size_t CtkScriptParser::MatcherArgumentContext::getRuleIndex() const {
  return CtkScriptParser::RuleMatcherArgument;
}


std::any CtkScriptParser::MatcherArgumentContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitMatcherArgument(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::MatcherArgumentContext* CtkScriptParser::matcherArgument() {
  MatcherArgumentContext *_localctx = _tracker.createInstance<MatcherArgumentContext>(_ctx, getState());
  enterRule(_localctx, 14, CtkScriptParser::RuleMatcherArgument);

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    setState(141);
    _errHandler->sync(this);
    switch (getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(_input, 16, _ctx)) {
    case 1: {
      enterOuterAlt(_localctx, 1);
      setState(138);
      matcherExpression();
      break;
    }

    case 2: {
      enterOuterAlt(_localctx, 2);
      setState(139);
      scalar();
      break;
    }

    case 3: {
      enterOuterAlt(_localctx, 3);
      setState(140);
      match(CtkScriptParser::Identifier);
      break;
    }

    default:
      break;
    }
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- ArgumentsContext ------------------------------------------------------------------

CtkScriptParser::ArgumentsContext::ArgumentsContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

std::vector<CtkScriptParser::ArgumentContext *> CtkScriptParser::ArgumentsContext::argument() {
  return getRuleContexts<CtkScriptParser::ArgumentContext>();
}

CtkScriptParser::ArgumentContext* CtkScriptParser::ArgumentsContext::argument(size_t i) {
  return getRuleContext<CtkScriptParser::ArgumentContext>(i);
}


size_t CtkScriptParser::ArgumentsContext::getRuleIndex() const {
  return CtkScriptParser::RuleArguments;
}


std::any CtkScriptParser::ArgumentsContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitArguments(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::ArgumentsContext* CtkScriptParser::arguments() {
  ArgumentsContext *_localctx = _tracker.createInstance<ArgumentsContext>(_ctx, getState());
  enterRule(_localctx, 16, CtkScriptParser::RuleArguments);
  size_t _la = 0;

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    enterOuterAlt(_localctx, 1);
    setState(143);
    argument();
    setState(148);
    _errHandler->sync(this);
    _la = _input->LA(1);
    while (_la == CtkScriptParser::T__17) {
      setState(144);
      match(CtkScriptParser::T__17);
      setState(145);
      argument();
      setState(150);
      _errHandler->sync(this);
      _la = _input->LA(1);
    }
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- ArgumentContext ------------------------------------------------------------------

CtkScriptParser::ArgumentContext::ArgumentContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}


size_t CtkScriptParser::ArgumentContext::getRuleIndex() const {
  return CtkScriptParser::RuleArgument;
}

void CtkScriptParser::ArgumentContext::copyFrom(ArgumentContext *ctx) {
  ParserRuleContext::copyFrom(ctx);
}

//----------------- PositionalArgumentContext ------------------------------------------------------------------

CtkScriptParser::ExpressionContext* CtkScriptParser::PositionalArgumentContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::PositionalArgumentContext::PositionalArgumentContext(ArgumentContext *ctx) { copyFrom(ctx); }


std::any CtkScriptParser::PositionalArgumentContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitPositionalArgument(this);
  else
    return visitor->visitChildren(this);
}
//----------------- NamedArgumentContext ------------------------------------------------------------------

tree::TerminalNode* CtkScriptParser::NamedArgumentContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

CtkScriptParser::ExpressionContext* CtkScriptParser::NamedArgumentContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::NamedArgumentContext::NamedArgumentContext(ArgumentContext *ctx) { copyFrom(ctx); }


std::any CtkScriptParser::NamedArgumentContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitNamedArgument(this);
  else
    return visitor->visitChildren(this);
}
CtkScriptParser::ArgumentContext* CtkScriptParser::argument() {
  ArgumentContext *_localctx = _tracker.createInstance<ArgumentContext>(_ctx, getState());
  enterRule(_localctx, 18, CtkScriptParser::RuleArgument);

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    setState(155);
    _errHandler->sync(this);
    switch (getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(_input, 18, _ctx)) {
    case 1: {
      _localctx = _tracker.createInstance<CtkScriptParser::NamedArgumentContext>(_localctx);
      enterOuterAlt(_localctx, 1);
      setState(151);
      match(CtkScriptParser::Identifier);
      setState(152);
      match(CtkScriptParser::T__1);
      setState(153);
      expression();
      break;
    }

    case 2: {
      _localctx = _tracker.createInstance<CtkScriptParser::PositionalArgumentContext>(_localctx);
      enterOuterAlt(_localctx, 2);
      setState(154);
      expression();
      break;
    }

    default:
      break;
    }
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- ScalarContext ------------------------------------------------------------------

CtkScriptParser::ScalarContext::ScalarContext(ParserRuleContext *parent, size_t invokingState)
  : ParserRuleContext(parent, invokingState) {
}

tree::TerminalNode* CtkScriptParser::ScalarContext::StringLiteral() {
  return getToken(CtkScriptParser::StringLiteral, 0);
}

tree::TerminalNode* CtkScriptParser::ScalarContext::Number() {
  return getToken(CtkScriptParser::Number, 0);
}


size_t CtkScriptParser::ScalarContext::getRuleIndex() const {
  return CtkScriptParser::RuleScalar;
}


std::any CtkScriptParser::ScalarContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor*>(visitor))
    return parserVisitor->visitScalar(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::ScalarContext* CtkScriptParser::scalar() {
  ScalarContext *_localctx = _tracker.createInstance<ScalarContext>(_ctx, getState());
  enterRule(_localctx, 20, CtkScriptParser::RuleScalar);
  size_t _la = 0;

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    enterOuterAlt(_localctx, 1);
    setState(157);
    _la = _input->LA(1);
    if (!((((_la & ~ 0x3fULL) == 0) &&
      ((1ULL << _la) & 14155776) != 0))) {
    _errHandler->recoverInline(this);
    }
    else {
      _errHandler->reportMatch(this);
      consume();
    }
   
  }
  catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

void CtkScriptParser::initialize() {
#if ANTLR4_USE_THREAD_LOCAL_CACHE
  ctkscriptParserInitialize();
#else
  ::antlr4::internal::call_once(ctkscriptParserOnceFlag, ctkscriptParserInitialize);
#endif
}
