
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

  CtkScriptParserStaticData(const CtkScriptParserStaticData &) = delete;
  CtkScriptParserStaticData(CtkScriptParserStaticData &&) = delete;
  CtkScriptParserStaticData &
  operator=(const CtkScriptParserStaticData &) = delete;
  CtkScriptParserStaticData &operator=(CtkScriptParserStaticData &&) = delete;

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
    std::unique_ptr<CtkScriptParserStaticData>
        ctkscriptParserStaticData = nullptr;

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
          "program", "statement", "expression", "functionName",
          "batchErrorPolicy", "progressPolicy", "matcherExpression",
          "matcherArguments", "matcherArgument", "arguments", "argument",
          "scalar", "memberName", "objectKey"},
      std::vector<std::string>{
          "",         "'let'",   "'='",     "';'",        "'emit'",
          "'save'",   "'to'",    "'as'",    "'foreach'",  "'in'",
          "'{'",      "'}'",     "'$'",     "'['",        "']'",
          "','",      "':'",     "'files'", "'do'",       "'('",
          "')'",      "'batch'", "'size'",  "'count'",    "'jobs'",
          "'memory'", "'on'",    "'error'", "'progress'", "'parse'",
          "'match'",  "'.'",     "'yield'", "'continue'", "'stop'",
          "'off'",    "'true'",  "'false'"},
      std::vector<std::string>{
          "",       "",           "",       "",           "",
          "",       "",           "",       "",           "",
          "",       "",           "",       "",           "",
          "",       "",           "",       "",           "",
          "",       "",           "",       "",           "",
          "",       "",           "",       "",           "",
          "",       "",           "",       "",           "",
          "",       "",           "",       "Identifier", "StringLiteral",
          "Number", "Whitespace", "Comment"});
  static const int32_t serializedATNSegment[] = {
      4,   1,   42,  271, 2,   0,   7,   0,   2,   1,   7,   1,   2,   2,   7,
      2,   2,   3,   7,   3,   2,   4,   7,   4,   2,   5,   7,   5,   2,   6,
      7,   6,   2,   7,   7,   7,   2,   8,   7,   8,   2,   9,   7,   9,   2,
      10,  7,   10,  2,   11,  7,   11,  2,   12,  7,   12,  2,   13,  7,   13,
      1,   0,   5,   0,   30,  8,   0,   10,  0,   12,  0,   33,  9,   0,   1,
      0,   1,   0,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
      1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
      1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,
      1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   5,   1,   64,
      8,   1,   10,  1,   12,  1,   67,  9,   1,   1,   1,   1,   1,   3,   1,
      71,  8,   1,   1,   2,   1,   2,   1,   2,   3,   2,   76,  8,   2,   1,
      2,   1,   2,   1,   2,   1,   2,   3,   2,   82,  8,   2,   1,   2,   1,
      2,   1,   2,   1,   2,   5,   2,   88,  8,   2,   10,  2,   12,  2,   91,
      9,   2,   3,   2,   93,  8,   2,   1,   2,   1,   2,   1,   2,   1,   2,
      1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   5,   2,   105,
      8,   2,   10,  2,   12,  2,   108, 9,   2,   3,   2,   110, 8,   2,   1,
      2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,
      1,   2,   1,   2,   5,   2,   122, 8,   2,   10,  2,   12,  2,   125, 9,
      2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,
      1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   3,
      2,   141, 8,   2,   1,   2,   1,   2,   3,   2,   145, 8,   2,   1,   2,
      1,   2,   3,   2,   149, 8,   2,   1,   2,   1,   2,   1,   2,   3,   2,
      154, 8,   2,   1,   2,   1,   2,   3,   2,   158, 8,   2,   1,   2,   1,
      2,   1,   2,   5,   2,   163, 8,   2,   10,  2,   12,  2,   166, 9,   2,
      1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   3,   2,   173, 8,   2,
      1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   1,
      2,   3,   2,   183, 8,   2,   1,   2,   1,   2,   1,   2,   1,   2,   5,
      2,   189, 8,   2,   10,  2,   12,  2,   192, 9,   2,   1,   2,   1,   2,
      1,   2,   1,   2,   1,   2,   3,   2,   199, 8,   2,   1,   2,   1,   2,
      1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   1,   2,   5,   2,   209,
      8,   2,   10,  2,   12,  2,   212, 9,   2,   1,   3,   1,   3,   1,   4,
      1,   4,   1,   5,   1,   5,   1,   6,   1,   6,   1,   6,   3,   6,   223,
      8,   6,   1,   6,   1,   6,   1,   6,   1,   6,   1,   6,   3,   6,   230,
      8,   6,   1,   6,   5,   6,   233, 8,   6,   10,  6,   12,  6,   236, 9,
      6,   1,   7,   1,   7,   1,   7,   5,   7,   241, 8,   7,   10,  7,   12,
      7,   244, 9,   7,   1,   8,   1,   8,   1,   8,   3,   8,   249, 8,   8,
      1,   9,   1,   9,   1,   9,   5,   9,   254, 8,   9,   10,  9,   12,  9,
      257, 9,   9,   1,   10,  1,   10,  1,   10,  1,   10,  3,   10,  263, 8,
      10,  1,   11,  1,   11,  1,   12,  1,   12,  1,   13,  1,   13,  1,   13,
      0,   1,   4,   14,  0,   2,   4,   6,   8,   10,  12,  14,  16,  18,  20,
      22,  24,  26,  0,   6,   4,   0,   23,  23,  30,  30,  33,  33,  38,  38,
      1,   0,   33,  34,  2,   0,   26,  26,  35,  35,  2,   0,   36,  37,  39,
      40,  3,   0,   23,  23,  33,  33,  38,  38,  3,   0,   23,  23,  33,  33,
      38,  39,  299, 0,   31,  1,   0,   0,   0,   2,   70,  1,   0,   0,   0,
      4,   198, 1,   0,   0,   0,   6,   213, 1,   0,   0,   0,   8,   215, 1,
      0,   0,   0,   10,  217, 1,   0,   0,   0,   12,  219, 1,   0,   0,   0,
      14,  237, 1,   0,   0,   0,   16,  248, 1,   0,   0,   0,   18,  250, 1,
      0,   0,   0,   20,  262, 1,   0,   0,   0,   22,  264, 1,   0,   0,   0,
      24,  266, 1,   0,   0,   0,   26,  268, 1,   0,   0,   0,   28,  30,  3,
      2,   1,   0,   29,  28,  1,   0,   0,   0,   30,  33,  1,   0,   0,   0,
      31,  29,  1,   0,   0,   0,   31,  32,  1,   0,   0,   0,   32,  34,  1,
      0,   0,   0,   33,  31,  1,   0,   0,   0,   34,  35,  5,   0,   0,   1,
      35,  1,   1,   0,   0,   0,   36,  37,  5,   1,   0,   0,   37,  38,  5,
      38,  0,   0,   38,  39,  5,   2,   0,   0,   39,  40,  3,   4,   2,   0,
      40,  41,  5,   3,   0,   0,   41,  71,  1,   0,   0,   0,   42,  43,  5,
      4,   0,   0,   43,  44,  3,   4,   2,   0,   44,  45,  5,   3,   0,   0,
      45,  71,  1,   0,   0,   0,   46,  47,  5,   5,   0,   0,   47,  48,  3,
      4,   2,   0,   48,  49,  5,   6,   0,   0,   49,  50,  3,   4,   2,   0,
      50,  51,  5,   7,   0,   0,   51,  52,  5,   38,  0,   0,   52,  53,  5,
      3,   0,   0,   53,  71,  1,   0,   0,   0,   54,  55,  3,   4,   2,   0,
      55,  56,  5,   3,   0,   0,   56,  71,  1,   0,   0,   0,   57,  58,  5,
      8,   0,   0,   58,  59,  5,   38,  0,   0,   59,  60,  5,   9,   0,   0,
      60,  61,  3,   4,   2,   0,   61,  65,  5,   10,  0,   0,   62,  64,  3,
      2,   1,   0,   63,  62,  1,   0,   0,   0,   64,  67,  1,   0,   0,   0,
      65,  63,  1,   0,   0,   0,   65,  66,  1,   0,   0,   0,   66,  68,  1,
      0,   0,   0,   67,  65,  1,   0,   0,   0,   68,  69,  5,   11,  0,   0,
      69,  71,  1,   0,   0,   0,   70,  36,  1,   0,   0,   0,   70,  42,  1,
      0,   0,   0,   70,  46,  1,   0,   0,   0,   70,  54,  1,   0,   0,   0,
      70,  57,  1,   0,   0,   0,   71,  3,   1,   0,   0,   0,   72,  73,  6,
      2,   -1,  0,   73,  199, 3,   22,  11,  0,   74,  76,  5,   12,  0,   0,
      75,  74,  1,   0,   0,   0,   75,  76,  1,   0,   0,   0,   76,  77,  1,
      0,   0,   0,   77,  81,  5,   38,  0,   0,   78,  79,  5,   13,  0,   0,
      79,  80,  5,   40,  0,   0,   80,  82,  5,   14,  0,   0,   81,  78,  1,
      0,   0,   0,   81,  82,  1,   0,   0,   0,   82,  199, 1,   0,   0,   0,
      83,  92,  5,   13,  0,   0,   84,  89,  3,   4,   2,   0,   85,  86,  5,
      15,  0,   0,   86,  88,  3,   4,   2,   0,   87,  85,  1,   0,   0,   0,
      88,  91,  1,   0,   0,   0,   89,  87,  1,   0,   0,   0,   89,  90,  1,
      0,   0,   0,   90,  93,  1,   0,   0,   0,   91,  89,  1,   0,   0,   0,
      92,  84,  1,   0,   0,   0,   92,  93,  1,   0,   0,   0,   93,  94,  1,
      0,   0,   0,   94,  199, 5,   14,  0,   0,   95,  109, 5,   10,  0,   0,
      96,  97,  3,   26,  13,  0,   97,  98,  5,   16,  0,   0,   98,  106, 3,
      4,   2,   0,   99,  100, 5,   15,  0,   0,   100, 101, 3,   26,  13,  0,
      101, 102, 5,   16,  0,   0,   102, 103, 3,   4,   2,   0,   103, 105, 1,
      0,   0,   0,   104, 99,  1,   0,   0,   0,   105, 108, 1,   0,   0,   0,
      106, 104, 1,   0,   0,   0,   106, 107, 1,   0,   0,   0,   107, 110, 1,
      0,   0,   0,   108, 106, 1,   0,   0,   0,   109, 96,  1,   0,   0,   0,
      109, 110, 1,   0,   0,   0,   110, 111, 1,   0,   0,   0,   111, 199, 5,
      11,  0,   0,   112, 113, 5,   17,  0,   0,   113, 199, 3,   4,   2,   10,
      114, 115, 5,   8,   0,   0,   115, 116, 5,   38,  0,   0,   116, 117, 5,
      9,   0,   0,   117, 118, 3,   4,   2,   0,   118, 119, 5,   18,  0,   0,
      119, 123, 5,   10,  0,   0,   120, 122, 3,   2,   1,   0,   121, 120, 1,
      0,   0,   0,   122, 125, 1,   0,   0,   0,   123, 121, 1,   0,   0,   0,
      123, 124, 1,   0,   0,   0,   124, 126, 1,   0,   0,   0,   125, 123, 1,
      0,   0,   0,   126, 127, 5,   11,  0,   0,   127, 199, 1,   0,   0,   0,
      128, 129, 5,   19,  0,   0,   129, 130, 3,   4,   2,   0,   130, 131, 5,
      20,  0,   0,   131, 199, 1,   0,   0,   0,   132, 133, 5,   21,  0,   0,
      133, 134, 5,   38,  0,   0,   134, 135, 5,   9,   0,   0,   135, 140, 3,
      4,   2,   0,   136, 137, 5,   22,  0,   0,   137, 141, 5,   40,  0,   0,
      138, 139, 5,   23,  0,   0,   139, 141, 5,   40,  0,   0,   140, 136, 1,
      0,   0,   0,   140, 138, 1,   0,   0,   0,   141, 144, 1,   0,   0,   0,
      142, 143, 5,   24,  0,   0,   143, 145, 5,   40,  0,   0,   144, 142, 1,
      0,   0,   0,   144, 145, 1,   0,   0,   0,   145, 148, 1,   0,   0,   0,
      146, 147, 5,   25,  0,   0,   147, 149, 5,   39,  0,   0,   148, 146, 1,
      0,   0,   0,   148, 149, 1,   0,   0,   0,   149, 153, 1,   0,   0,   0,
      150, 151, 5,   26,  0,   0,   151, 152, 5,   27,  0,   0,   152, 154, 3,
      8,   4,   0,   153, 150, 1,   0,   0,   0,   153, 154, 1,   0,   0,   0,
      154, 157, 1,   0,   0,   0,   155, 156, 5,   28,  0,   0,   156, 158, 3,
      10,  5,   0,   157, 155, 1,   0,   0,   0,   157, 158, 1,   0,   0,   0,
      158, 159, 1,   0,   0,   0,   159, 160, 5,   18,  0,   0,   160, 164, 5,
      10,  0,   0,   161, 163, 3,   2,   1,   0,   162, 161, 1,   0,   0,   0,
      163, 166, 1,   0,   0,   0,   164, 162, 1,   0,   0,   0,   164, 165, 1,
      0,   0,   0,   165, 167, 1,   0,   0,   0,   166, 164, 1,   0,   0,   0,
      167, 168, 5,   11,  0,   0,   168, 199, 1,   0,   0,   0,   169, 170, 3,
      6,   3,   0,   170, 172, 5,   19,  0,   0,   171, 173, 3,   18,  9,   0,
      172, 171, 1,   0,   0,   0,   172, 173, 1,   0,   0,   0,   173, 174, 1,
      0,   0,   0,   174, 175, 5,   20,  0,   0,   175, 199, 1,   0,   0,   0,
      176, 177, 5,   29,  0,   0,   177, 199, 5,   39,  0,   0,   178, 179, 5,
      30,  0,   0,   179, 182, 3,   12,  6,   0,   180, 181, 5,   9,   0,   0,
      181, 183, 3,   4,   2,   0,   182, 180, 1,   0,   0,   0,   182, 183, 1,
      0,   0,   0,   183, 199, 1,   0,   0,   0,   184, 185, 5,   9,   0,   0,
      185, 186, 3,   4,   2,   0,   186, 190, 5,   10,  0,   0,   187, 189, 3,
      2,   1,   0,   188, 187, 1,   0,   0,   0,   189, 192, 1,   0,   0,   0,
      190, 188, 1,   0,   0,   0,   190, 191, 1,   0,   0,   0,   191, 193, 1,
      0,   0,   0,   192, 190, 1,   0,   0,   0,   193, 194, 5,   32,  0,   0,
      194, 195, 3,   4,   2,   0,   195, 196, 5,   3,   0,   0,   196, 197, 5,
      11,  0,   0,   197, 199, 1,   0,   0,   0,   198, 72,  1,   0,   0,   0,
      198, 75,  1,   0,   0,   0,   198, 83,  1,   0,   0,   0,   198, 95,  1,
      0,   0,   0,   198, 112, 1,   0,   0,   0,   198, 114, 1,   0,   0,   0,
      198, 128, 1,   0,   0,   0,   198, 132, 1,   0,   0,   0,   198, 169, 1,
      0,   0,   0,   198, 176, 1,   0,   0,   0,   198, 178, 1,   0,   0,   0,
      198, 184, 1,   0,   0,   0,   199, 210, 1,   0,   0,   0,   200, 201, 10,
      3,   0,   0,   201, 202, 5,   31,  0,   0,   202, 209, 3,   24,  12,  0,
      203, 204, 10,  2,   0,   0,   204, 205, 5,   13,  0,   0,   205, 206, 3,
      4,   2,   0,   206, 207, 5,   14,  0,   0,   207, 209, 1,   0,   0,   0,
      208, 200, 1,   0,   0,   0,   208, 203, 1,   0,   0,   0,   209, 212, 1,
      0,   0,   0,   210, 208, 1,   0,   0,   0,   210, 211, 1,   0,   0,   0,
      211, 5,   1,   0,   0,   0,   212, 210, 1,   0,   0,   0,   213, 214, 7,
      0,   0,   0,   214, 7,   1,   0,   0,   0,   215, 216, 7,   1,   0,   0,
      216, 9,   1,   0,   0,   0,   217, 218, 7,   2,   0,   0,   218, 11,  1,
      0,   0,   0,   219, 220, 5,   38,  0,   0,   220, 222, 5,   19,  0,   0,
      221, 223, 3,   14,  7,   0,   222, 221, 1,   0,   0,   0,   222, 223, 1,
      0,   0,   0,   223, 224, 1,   0,   0,   0,   224, 234, 5,   20,  0,   0,
      225, 226, 5,   31,  0,   0,   226, 227, 5,   38,  0,   0,   227, 229, 5,
      19,  0,   0,   228, 230, 3,   14,  7,   0,   229, 228, 1,   0,   0,   0,
      229, 230, 1,   0,   0,   0,   230, 231, 1,   0,   0,   0,   231, 233, 5,
      20,  0,   0,   232, 225, 1,   0,   0,   0,   233, 236, 1,   0,   0,   0,
      234, 232, 1,   0,   0,   0,   234, 235, 1,   0,   0,   0,   235, 13,  1,
      0,   0,   0,   236, 234, 1,   0,   0,   0,   237, 242, 3,   16,  8,   0,
      238, 239, 5,   15,  0,   0,   239, 241, 3,   16,  8,   0,   240, 238, 1,
      0,   0,   0,   241, 244, 1,   0,   0,   0,   242, 240, 1,   0,   0,   0,
      242, 243, 1,   0,   0,   0,   243, 15,  1,   0,   0,   0,   244, 242, 1,
      0,   0,   0,   245, 249, 3,   12,  6,   0,   246, 249, 3,   22,  11,  0,
      247, 249, 5,   38,  0,   0,   248, 245, 1,   0,   0,   0,   248, 246, 1,
      0,   0,   0,   248, 247, 1,   0,   0,   0,   249, 17,  1,   0,   0,   0,
      250, 255, 3,   20,  10,  0,   251, 252, 5,   15,  0,   0,   252, 254, 3,
      20,  10,  0,   253, 251, 1,   0,   0,   0,   254, 257, 1,   0,   0,   0,
      255, 253, 1,   0,   0,   0,   255, 256, 1,   0,   0,   0,   256, 19,  1,
      0,   0,   0,   257, 255, 1,   0,   0,   0,   258, 259, 5,   38,  0,   0,
      259, 260, 5,   2,   0,   0,   260, 263, 3,   4,   2,   0,   261, 263, 3,
      4,   2,   0,   262, 258, 1,   0,   0,   0,   262, 261, 1,   0,   0,   0,
      263, 21,  1,   0,   0,   0,   264, 265, 7,   3,   0,   0,   265, 23,  1,
      0,   0,   0,   266, 267, 7,   4,   0,   0,   267, 25,  1,   0,   0,   0,
      268, 269, 7,   5,   0,   0,   269, 27,  1,   0,   0,   0,   29,  31,  65,
      70,  75,  81,  89,  92,  106, 109, 123, 140, 144, 148, 153, 157, 164, 172,
      182, 190, 198, 208, 210, 222, 229, 234, 242, 248, 255, 262};
  staticData->serializedATN = antlr4::atn::SerializedATNView(
      serializedATNSegment,
      sizeof(serializedATNSegment) / sizeof(serializedATNSegment[0]));

  antlr4::atn::ATNDeserializer deserializer;
  staticData->atn = deserializer.deserialize(staticData->serializedATN);

  const size_t count = staticData->atn->getNumberOfDecisions();
  staticData->decisionToDFA.reserve(count);
  for (size_t i = 0; i < count; i++) {
    staticData->decisionToDFA.emplace_back(staticData->atn->getDecisionState(i),
                                           i);
  }
  ctkscriptParserStaticData = std::move(staticData);
}

} // namespace

CtkScriptParser::CtkScriptParser(TokenStream *input)
    : CtkScriptParser(input, antlr4::atn::ParserATNSimulatorOptions()) {}

CtkScriptParser::CtkScriptParser(
    TokenStream *input, const antlr4::atn::ParserATNSimulatorOptions &options)
    : Parser(input) {
  CtkScriptParser::initialize();
  _interpreter = new atn::ParserATNSimulator(
      this, *ctkscriptParserStaticData->atn,
      ctkscriptParserStaticData->decisionToDFA,
      ctkscriptParserStaticData->sharedContextCache, options);
}

CtkScriptParser::~CtkScriptParser() { delete _interpreter; }

const atn::ATN &CtkScriptParser::getATN() const {
  return *ctkscriptParserStaticData->atn;
}

std::string CtkScriptParser::getGrammarFileName() const {
  return "CtkScript.g4";
}

const std::vector<std::string> &CtkScriptParser::getRuleNames() const {
  return ctkscriptParserStaticData->ruleNames;
}

const dfa::Vocabulary &CtkScriptParser::getVocabulary() const {
  return ctkscriptParserStaticData->vocabulary;
}

antlr4::atn::SerializedATNView CtkScriptParser::getSerializedATN() const {
  return ctkscriptParserStaticData->serializedATN;
}

//----------------- ProgramContext
//------------------------------------------------------------------

CtkScriptParser::ProgramContext::ProgramContext(ParserRuleContext *parent,
                                                size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

tree::TerminalNode *CtkScriptParser::ProgramContext::EOF() {
  return getToken(CtkScriptParser::EOF, 0);
}

std::vector<CtkScriptParser::StatementContext *>
CtkScriptParser::ProgramContext::statement() {
  return getRuleContexts<CtkScriptParser::StatementContext>();
}

CtkScriptParser::StatementContext *
CtkScriptParser::ProgramContext::statement(size_t i) {
  return getRuleContext<CtkScriptParser::StatementContext>(i);
}

size_t CtkScriptParser::ProgramContext::getRuleIndex() const {
  return CtkScriptParser::RuleProgram;
}

std::any
CtkScriptParser::ProgramContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitProgram(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::ProgramContext *CtkScriptParser::program() {
  ProgramContext *_localctx =
      _tracker.createInstance<ProgramContext>(_ctx, getState());
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
    setState(31);
    _errHandler->sync(this);
    _la = _input->LA(1);
    while ((((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 2140515481394) != 0)) {
      setState(28);
      statement();
      setState(33);
      _errHandler->sync(this);
      _la = _input->LA(1);
    }
    setState(34);
    match(CtkScriptParser::EOF);

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- StatementContext
//------------------------------------------------------------------

CtkScriptParser::StatementContext::StatementContext(ParserRuleContext *parent,
                                                    size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

size_t CtkScriptParser::StatementContext::getRuleIndex() const {
  return CtkScriptParser::RuleStatement;
}

void CtkScriptParser::StatementContext::copyFrom(StatementContext *ctx) {
  ParserRuleContext::copyFrom(ctx);
}

//----------------- EmissionContext
//------------------------------------------------------------------

CtkScriptParser::ExpressionContext *
CtkScriptParser::EmissionContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::EmissionContext::EmissionContext(StatementContext *ctx) {
  copyFrom(ctx);
}

std::any
CtkScriptParser::EmissionContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitEmission(this);
  else
    return visitor->visitChildren(this);
}
//----------------- ValueStatementContext
//------------------------------------------------------------------

CtkScriptParser::ExpressionContext *
CtkScriptParser::ValueStatementContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::ValueStatementContext::ValueStatementContext(
    StatementContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::ValueStatementContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitValueStatement(this);
  else
    return visitor->visitChildren(this);
}
//----------------- AssignmentContext
//------------------------------------------------------------------

tree::TerminalNode *CtkScriptParser::AssignmentContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::AssignmentContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::AssignmentContext::AssignmentContext(StatementContext *ctx) {
  copyFrom(ctx);
}

std::any
CtkScriptParser::AssignmentContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitAssignment(this);
  else
    return visitor->visitChildren(this);
}
//----------------- IterationContext
//------------------------------------------------------------------

tree::TerminalNode *CtkScriptParser::IterationContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::IterationContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

std::vector<CtkScriptParser::StatementContext *>
CtkScriptParser::IterationContext::statement() {
  return getRuleContexts<CtkScriptParser::StatementContext>();
}

CtkScriptParser::StatementContext *
CtkScriptParser::IterationContext::statement(size_t i) {
  return getRuleContext<CtkScriptParser::StatementContext>(i);
}

CtkScriptParser::IterationContext::IterationContext(StatementContext *ctx) {
  copyFrom(ctx);
}

std::any
CtkScriptParser::IterationContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitIteration(this);
  else
    return visitor->visitChildren(this);
}
//----------------- SaveStatementContext
//------------------------------------------------------------------

std::vector<CtkScriptParser::ExpressionContext *>
CtkScriptParser::SaveStatementContext::expression() {
  return getRuleContexts<CtkScriptParser::ExpressionContext>();
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::SaveStatementContext::expression(size_t i) {
  return getRuleContext<CtkScriptParser::ExpressionContext>(i);
}

tree::TerminalNode *CtkScriptParser::SaveStatementContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

CtkScriptParser::SaveStatementContext::SaveStatementContext(
    StatementContext *ctx) {
  copyFrom(ctx);
}

std::any
CtkScriptParser::SaveStatementContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitSaveStatement(this);
  else
    return visitor->visitChildren(this);
}
CtkScriptParser::StatementContext *CtkScriptParser::statement() {
  StatementContext *_localctx =
      _tracker.createInstance<StatementContext>(_ctx, getState());
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
    setState(70);
    _errHandler->sync(this);
    switch (getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(
        _input, 2, _ctx)) {
    case 1: {
      _localctx = _tracker.createInstance<CtkScriptParser::AssignmentContext>(
          _localctx);
      enterOuterAlt(_localctx, 1);
      setState(36);
      match(CtkScriptParser::T__0);
      setState(37);
      match(CtkScriptParser::Identifier);
      setState(38);
      match(CtkScriptParser::T__1);
      setState(39);
      expression(0);
      setState(40);
      match(CtkScriptParser::T__2);
      break;
    }

    case 2: {
      _localctx =
          _tracker.createInstance<CtkScriptParser::EmissionContext>(_localctx);
      enterOuterAlt(_localctx, 2);
      setState(42);
      match(CtkScriptParser::T__3);
      setState(43);
      expression(0);
      setState(44);
      match(CtkScriptParser::T__2);
      break;
    }

    case 3: {
      _localctx =
          _tracker.createInstance<CtkScriptParser::SaveStatementContext>(
              _localctx);
      enterOuterAlt(_localctx, 3);
      setState(46);
      match(CtkScriptParser::T__4);
      setState(47);
      expression(0);
      setState(48);
      match(CtkScriptParser::T__5);
      setState(49);
      expression(0);
      setState(50);
      match(CtkScriptParser::T__6);
      setState(51);
      match(CtkScriptParser::Identifier);
      setState(52);
      match(CtkScriptParser::T__2);
      break;
    }

    case 4: {
      _localctx =
          _tracker.createInstance<CtkScriptParser::ValueStatementContext>(
              _localctx);
      enterOuterAlt(_localctx, 4);
      setState(54);
      expression(0);
      setState(55);
      match(CtkScriptParser::T__2);
      break;
    }

    case 5: {
      _localctx =
          _tracker.createInstance<CtkScriptParser::IterationContext>(_localctx);
      enterOuterAlt(_localctx, 5);
      setState(57);
      match(CtkScriptParser::T__7);
      setState(58);
      match(CtkScriptParser::Identifier);
      setState(59);
      match(CtkScriptParser::T__8);
      setState(60);
      expression(0);
      setState(61);
      match(CtkScriptParser::T__9);
      setState(65);
      _errHandler->sync(this);
      _la = _input->LA(1);
      while (
          (((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 2140515481394) != 0)) {
        setState(62);
        statement();
        setState(67);
        _errHandler->sync(this);
        _la = _input->LA(1);
      }
      setState(68);
      match(CtkScriptParser::T__10);
      break;
    }

    default:
      break;
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- ExpressionContext
//------------------------------------------------------------------

CtkScriptParser::ExpressionContext::ExpressionContext(ParserRuleContext *parent,
                                                      size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

size_t CtkScriptParser::ExpressionContext::getRuleIndex() const {
  return CtkScriptParser::RuleExpression;
}

void CtkScriptParser::ExpressionContext::copyFrom(ExpressionContext *ctx) {
  ParserRuleContext::copyFrom(ctx);
}

//----------------- MatchExpressionContext
//------------------------------------------------------------------

CtkScriptParser::MatcherExpressionContext *
CtkScriptParser::MatchExpressionContext::matcherExpression() {
  return getRuleContext<CtkScriptParser::MatcherExpressionContext>(0);
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::MatchExpressionContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::MatchExpressionContext::MatchExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::MatchExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitMatchExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- BatchExpressionContext
//------------------------------------------------------------------

tree::TerminalNode *CtkScriptParser::BatchExpressionContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::BatchExpressionContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

std::vector<tree::TerminalNode *>
CtkScriptParser::BatchExpressionContext::Number() {
  return getTokens(CtkScriptParser::Number);
}

tree::TerminalNode *CtkScriptParser::BatchExpressionContext::Number(size_t i) {
  return getToken(CtkScriptParser::Number, i);
}

CtkScriptParser::BatchErrorPolicyContext *
CtkScriptParser::BatchExpressionContext::batchErrorPolicy() {
  return getRuleContext<CtkScriptParser::BatchErrorPolicyContext>(0);
}

CtkScriptParser::ProgressPolicyContext *
CtkScriptParser::BatchExpressionContext::progressPolicy() {
  return getRuleContext<CtkScriptParser::ProgressPolicyContext>(0);
}

std::vector<CtkScriptParser::StatementContext *>
CtkScriptParser::BatchExpressionContext::statement() {
  return getRuleContexts<CtkScriptParser::StatementContext>();
}

CtkScriptParser::StatementContext *
CtkScriptParser::BatchExpressionContext::statement(size_t i) {
  return getRuleContext<CtkScriptParser::StatementContext>(i);
}

tree::TerminalNode *CtkScriptParser::BatchExpressionContext::StringLiteral() {
  return getToken(CtkScriptParser::StringLiteral, 0);
}

CtkScriptParser::BatchExpressionContext::BatchExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::BatchExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitBatchExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- ReferenceExpressionContext
//------------------------------------------------------------------

tree::TerminalNode *CtkScriptParser::ReferenceExpressionContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

tree::TerminalNode *CtkScriptParser::ReferenceExpressionContext::Number() {
  return getToken(CtkScriptParser::Number, 0);
}

CtkScriptParser::ReferenceExpressionContext::ReferenceExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::ReferenceExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitReferenceExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- FilesExpressionContext
//------------------------------------------------------------------

CtkScriptParser::ExpressionContext *
CtkScriptParser::FilesExpressionContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::FilesExpressionContext::FilesExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::FilesExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitFilesExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- MemberExpressionContext
//------------------------------------------------------------------

CtkScriptParser::ExpressionContext *
CtkScriptParser::MemberExpressionContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::MemberNameContext *
CtkScriptParser::MemberExpressionContext::memberName() {
  return getRuleContext<CtkScriptParser::MemberNameContext>(0);
}

CtkScriptParser::MemberExpressionContext::MemberExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::MemberExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitMemberExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- GroupedExpressionContext
//------------------------------------------------------------------

CtkScriptParser::ExpressionContext *
CtkScriptParser::GroupedExpressionContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::GroupedExpressionContext::GroupedExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::GroupedExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitGroupedExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- ObjectExpressionContext
//------------------------------------------------------------------

std::vector<CtkScriptParser::ObjectKeyContext *>
CtkScriptParser::ObjectExpressionContext::objectKey() {
  return getRuleContexts<CtkScriptParser::ObjectKeyContext>();
}

CtkScriptParser::ObjectKeyContext *
CtkScriptParser::ObjectExpressionContext::objectKey(size_t i) {
  return getRuleContext<CtkScriptParser::ObjectKeyContext>(i);
}

std::vector<CtkScriptParser::ExpressionContext *>
CtkScriptParser::ObjectExpressionContext::expression() {
  return getRuleContexts<CtkScriptParser::ExpressionContext>();
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::ObjectExpressionContext::expression(size_t i) {
  return getRuleContext<CtkScriptParser::ExpressionContext>(i);
}

CtkScriptParser::ObjectExpressionContext::ObjectExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::ObjectExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitObjectExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- ForeachExpressionContext
//------------------------------------------------------------------

tree::TerminalNode *CtkScriptParser::ForeachExpressionContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::ForeachExpressionContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

std::vector<CtkScriptParser::StatementContext *>
CtkScriptParser::ForeachExpressionContext::statement() {
  return getRuleContexts<CtkScriptParser::StatementContext>();
}

CtkScriptParser::StatementContext *
CtkScriptParser::ForeachExpressionContext::statement(size_t i) {
  return getRuleContext<CtkScriptParser::StatementContext>(i);
}

CtkScriptParser::ForeachExpressionContext::ForeachExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::ForeachExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitForeachExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- CallExpressionContext
//------------------------------------------------------------------

CtkScriptParser::FunctionNameContext *
CtkScriptParser::CallExpressionContext::functionName() {
  return getRuleContext<CtkScriptParser::FunctionNameContext>(0);
}

CtkScriptParser::ArgumentsContext *
CtkScriptParser::CallExpressionContext::arguments() {
  return getRuleContext<CtkScriptParser::ArgumentsContext>(0);
}

CtkScriptParser::CallExpressionContext::CallExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::CallExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitCallExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- IndexExpressionContext
//------------------------------------------------------------------

std::vector<CtkScriptParser::ExpressionContext *>
CtkScriptParser::IndexExpressionContext::expression() {
  return getRuleContexts<CtkScriptParser::ExpressionContext>();
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::IndexExpressionContext::expression(size_t i) {
  return getRuleContext<CtkScriptParser::ExpressionContext>(i);
}

CtkScriptParser::IndexExpressionContext::IndexExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::IndexExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitIndexExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- LiteralExpressionContext
//------------------------------------------------------------------

CtkScriptParser::ScalarContext *
CtkScriptParser::LiteralExpressionContext::scalar() {
  return getRuleContext<CtkScriptParser::ScalarContext>(0);
}

CtkScriptParser::LiteralExpressionContext::LiteralExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::LiteralExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitLiteralExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- ListExpressionContext
//------------------------------------------------------------------

std::vector<CtkScriptParser::ExpressionContext *>
CtkScriptParser::ListExpressionContext::expression() {
  return getRuleContexts<CtkScriptParser::ExpressionContext>();
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::ListExpressionContext::expression(size_t i) {
  return getRuleContext<CtkScriptParser::ExpressionContext>(i);
}

CtkScriptParser::ListExpressionContext::ListExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::ListExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitListExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- ParseExpressionContext
//------------------------------------------------------------------

tree::TerminalNode *CtkScriptParser::ParseExpressionContext::StringLiteral() {
  return getToken(CtkScriptParser::StringLiteral, 0);
}

CtkScriptParser::ParseExpressionContext::ParseExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::ParseExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitParseExpression(this);
  else
    return visitor->visitChildren(this);
}
//----------------- ScopedExpressionContext
//------------------------------------------------------------------

std::vector<CtkScriptParser::ExpressionContext *>
CtkScriptParser::ScopedExpressionContext::expression() {
  return getRuleContexts<CtkScriptParser::ExpressionContext>();
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::ScopedExpressionContext::expression(size_t i) {
  return getRuleContext<CtkScriptParser::ExpressionContext>(i);
}

std::vector<CtkScriptParser::StatementContext *>
CtkScriptParser::ScopedExpressionContext::statement() {
  return getRuleContexts<CtkScriptParser::StatementContext>();
}

CtkScriptParser::StatementContext *
CtkScriptParser::ScopedExpressionContext::statement(size_t i) {
  return getRuleContext<CtkScriptParser::StatementContext>(i);
}

CtkScriptParser::ScopedExpressionContext::ScopedExpressionContext(
    ExpressionContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::ScopedExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitScopedExpression(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::ExpressionContext *CtkScriptParser::expression() {
  return expression(0);
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::expression(int precedence) {
  ParserRuleContext *parentContext = _ctx;
  size_t parentState = getState();
  CtkScriptParser::ExpressionContext *_localctx =
      _tracker.createInstance<ExpressionContext>(_ctx, parentState);
  CtkScriptParser::ExpressionContext *previousContext = _localctx;
  (void)previousContext; // Silence compiler, in case the context is not used by
                         // generated code.
  size_t startState = 4;
  enterRecursionRule(_localctx, 4, CtkScriptParser::RuleExpression, precedence);

  size_t _la = 0;

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    unrollRecursionContexts(parentContext);
  });
  try {
    size_t alt;
    enterOuterAlt(_localctx, 1);
    setState(198);
    _errHandler->sync(this);
    switch (getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(
        _input, 19, _ctx)) {
    case 1: {
      _localctx = _tracker.createInstance<LiteralExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;

      setState(73);
      scalar();
      break;
    }

    case 2: {
      _localctx =
          _tracker.createInstance<ReferenceExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;
      setState(75);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if (_la == CtkScriptParser::T__11) {
        setState(74);
        match(CtkScriptParser::T__11);
      }
      setState(77);
      match(CtkScriptParser::Identifier);
      setState(81);
      _errHandler->sync(this);

      switch (getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(
          _input, 4, _ctx)) {
      case 1: {
        setState(78);
        match(CtkScriptParser::T__12);
        setState(79);
        match(CtkScriptParser::Number);
        setState(80);
        match(CtkScriptParser::T__13);
        break;
      }

      default:
        break;
      }
      break;
    }

    case 3: {
      _localctx = _tracker.createInstance<ListExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;
      setState(83);
      match(CtkScriptParser::T__12);
      setState(92);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if ((((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 2140515481344) != 0)) {
        setState(84);
        expression(0);
        setState(89);
        _errHandler->sync(this);
        _la = _input->LA(1);
        while (_la == CtkScriptParser::T__14) {
          setState(85);
          match(CtkScriptParser::T__14);
          setState(86);
          expression(0);
          setState(91);
          _errHandler->sync(this);
          _la = _input->LA(1);
        }
      }
      setState(94);
      match(CtkScriptParser::T__13);
      break;
    }

    case 4: {
      _localctx = _tracker.createInstance<ObjectExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;
      setState(95);
      match(CtkScriptParser::T__9);
      setState(109);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if ((((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 833232044032) != 0)) {
        setState(96);
        objectKey();
        setState(97);
        match(CtkScriptParser::T__15);
        setState(98);
        expression(0);
        setState(106);
        _errHandler->sync(this);
        _la = _input->LA(1);
        while (_la == CtkScriptParser::T__14) {
          setState(99);
          match(CtkScriptParser::T__14);
          setState(100);
          objectKey();
          setState(101);
          match(CtkScriptParser::T__15);
          setState(102);
          expression(0);
          setState(108);
          _errHandler->sync(this);
          _la = _input->LA(1);
        }
      }
      setState(111);
      match(CtkScriptParser::T__10);
      break;
    }

    case 5: {
      _localctx = _tracker.createInstance<FilesExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;
      setState(112);
      match(CtkScriptParser::T__16);
      setState(113);
      expression(10);
      break;
    }

    case 6: {
      _localctx = _tracker.createInstance<ForeachExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;
      setState(114);
      match(CtkScriptParser::T__7);
      setState(115);
      match(CtkScriptParser::Identifier);
      setState(116);
      match(CtkScriptParser::T__8);
      setState(117);
      expression(0);
      setState(118);
      match(CtkScriptParser::T__17);
      setState(119);
      match(CtkScriptParser::T__9);
      setState(123);
      _errHandler->sync(this);
      _la = _input->LA(1);
      while (
          (((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 2140515481394) != 0)) {
        setState(120);
        statement();
        setState(125);
        _errHandler->sync(this);
        _la = _input->LA(1);
      }
      setState(126);
      match(CtkScriptParser::T__10);
      break;
    }

    case 7: {
      _localctx = _tracker.createInstance<GroupedExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;
      setState(128);
      match(CtkScriptParser::T__18);
      setState(129);
      expression(0);
      setState(130);
      match(CtkScriptParser::T__19);
      break;
    }

    case 8: {
      _localctx = _tracker.createInstance<BatchExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;
      setState(132);
      match(CtkScriptParser::T__20);
      setState(133);
      match(CtkScriptParser::Identifier);
      setState(134);
      match(CtkScriptParser::T__8);
      setState(135);
      expression(0);
      setState(140);
      _errHandler->sync(this);
      switch (_input->LA(1)) {
      case CtkScriptParser::T__21: {
        setState(136);
        match(CtkScriptParser::T__21);
        setState(137);
        antlrcpp::downCast<BatchExpressionContext *>(_localctx)->sizeValue =
            match(CtkScriptParser::Number);
        break;
      }

      case CtkScriptParser::T__22: {
        setState(138);
        match(CtkScriptParser::T__22);
        setState(139);
        antlrcpp::downCast<BatchExpressionContext *>(_localctx)->countValue =
            match(CtkScriptParser::Number);
        break;
      }

      default:
        throw NoViableAltException(this);
      }
      setState(144);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if (_la == CtkScriptParser::T__23) {
        setState(142);
        match(CtkScriptParser::T__23);
        setState(143);
        antlrcpp::downCast<BatchExpressionContext *>(_localctx)->jobsValue =
            match(CtkScriptParser::Number);
      }
      setState(148);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if (_la == CtkScriptParser::T__24) {
        setState(146);
        match(CtkScriptParser::T__24);
        setState(147);
        antlrcpp::downCast<BatchExpressionContext *>(_localctx)->memoryValue =
            match(CtkScriptParser::StringLiteral);
      }
      setState(153);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if (_la == CtkScriptParser::T__25) {
        setState(150);
        match(CtkScriptParser::T__25);
        setState(151);
        match(CtkScriptParser::T__26);
        setState(152);
        batchErrorPolicy();
      }
      setState(157);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if (_la == CtkScriptParser::T__27) {
        setState(155);
        match(CtkScriptParser::T__27);
        setState(156);
        progressPolicy();
      }
      setState(159);
      match(CtkScriptParser::T__17);
      setState(160);
      match(CtkScriptParser::T__9);
      setState(164);
      _errHandler->sync(this);
      _la = _input->LA(1);
      while (
          (((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 2140515481394) != 0)) {
        setState(161);
        statement();
        setState(166);
        _errHandler->sync(this);
        _la = _input->LA(1);
      }
      setState(167);
      match(CtkScriptParser::T__10);
      break;
    }

    case 9: {
      _localctx = _tracker.createInstance<CallExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;
      setState(169);
      functionName();
      setState(170);
      match(CtkScriptParser::T__18);
      setState(172);
      _errHandler->sync(this);

      _la = _input->LA(1);
      if ((((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 2140515481344) != 0)) {
        setState(171);
        arguments();
      }
      setState(174);
      match(CtkScriptParser::T__19);
      break;
    }

    case 10: {
      _localctx = _tracker.createInstance<ParseExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;
      setState(176);
      match(CtkScriptParser::T__28);
      setState(177);
      match(CtkScriptParser::StringLiteral);
      break;
    }

    case 11: {
      _localctx = _tracker.createInstance<MatchExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;
      setState(178);
      match(CtkScriptParser::T__29);
      setState(179);
      matcherExpression();
      setState(182);
      _errHandler->sync(this);

      switch (getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(
          _input, 17, _ctx)) {
      case 1: {
        setState(180);
        match(CtkScriptParser::T__8);
        setState(181);
        expression(0);
        break;
      }

      default:
        break;
      }
      break;
    }

    case 12: {
      _localctx = _tracker.createInstance<ScopedExpressionContext>(_localctx);
      _ctx = _localctx;
      previousContext = _localctx;
      setState(184);
      match(CtkScriptParser::T__8);
      setState(185);
      expression(0);
      setState(186);
      match(CtkScriptParser::T__9);
      setState(190);
      _errHandler->sync(this);
      _la = _input->LA(1);
      while (
          (((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 2140515481394) != 0)) {
        setState(187);
        statement();
        setState(192);
        _errHandler->sync(this);
        _la = _input->LA(1);
      }
      setState(193);
      match(CtkScriptParser::T__31);
      setState(194);
      expression(0);
      setState(195);
      match(CtkScriptParser::T__2);
      setState(196);
      match(CtkScriptParser::T__10);
      break;
    }

    default:
      break;
    }
    _ctx->stop = _input->LT(-1);
    setState(210);
    _errHandler->sync(this);
    alt = getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(_input, 21,
                                                                     _ctx);
    while (alt != 2 && alt != atn::ATN::INVALID_ALT_NUMBER) {
      if (alt == 1) {
        if (!_parseListeners.empty())
          triggerExitRuleEvent();
        previousContext = _localctx;
        setState(208);
        _errHandler->sync(this);
        switch (getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(
            _input, 20, _ctx)) {
        case 1: {
          auto newContext = _tracker.createInstance<MemberExpressionContext>(
              _tracker.createInstance<ExpressionContext>(parentContext,
                                                         parentState));
          _localctx = newContext;
          pushNewRecursionContext(newContext, startState, RuleExpression);
          setState(200);

          if (!(precpred(_ctx, 3)))
            throw FailedPredicateException(this, "precpred(_ctx, 3)");
          setState(201);
          match(CtkScriptParser::T__30);
          setState(202);
          memberName();
          break;
        }

        case 2: {
          auto newContext = _tracker.createInstance<IndexExpressionContext>(
              _tracker.createInstance<ExpressionContext>(parentContext,
                                                         parentState));
          _localctx = newContext;
          pushNewRecursionContext(newContext, startState, RuleExpression);
          setState(203);

          if (!(precpred(_ctx, 2)))
            throw FailedPredicateException(this, "precpred(_ctx, 2)");
          setState(204);
          match(CtkScriptParser::T__12);
          setState(205);
          expression(0);
          setState(206);
          match(CtkScriptParser::T__13);
          break;
        }

        default:
          break;
        }
      }
      setState(212);
      _errHandler->sync(this);
      alt = getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(
          _input, 21, _ctx);
    }
  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }
  return _localctx;
}

//----------------- FunctionNameContext
//------------------------------------------------------------------

CtkScriptParser::FunctionNameContext::FunctionNameContext(
    ParserRuleContext *parent, size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

tree::TerminalNode *CtkScriptParser::FunctionNameContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

size_t CtkScriptParser::FunctionNameContext::getRuleIndex() const {
  return CtkScriptParser::RuleFunctionName;
}

std::any
CtkScriptParser::FunctionNameContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitFunctionName(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::FunctionNameContext *CtkScriptParser::functionName() {
  FunctionNameContext *_localctx =
      _tracker.createInstance<FunctionNameContext>(_ctx, getState());
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
    setState(213);
    _la = _input->LA(1);
    if (!((((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 284549971968) != 0))) {
      _errHandler->recoverInline(this);
    } else {
      _errHandler->reportMatch(this);
      consume();
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- BatchErrorPolicyContext
//------------------------------------------------------------------

CtkScriptParser::BatchErrorPolicyContext::BatchErrorPolicyContext(
    ParserRuleContext *parent, size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

size_t CtkScriptParser::BatchErrorPolicyContext::getRuleIndex() const {
  return CtkScriptParser::RuleBatchErrorPolicy;
}

std::any CtkScriptParser::BatchErrorPolicyContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitBatchErrorPolicy(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::BatchErrorPolicyContext *CtkScriptParser::batchErrorPolicy() {
  BatchErrorPolicyContext *_localctx =
      _tracker.createInstance<BatchErrorPolicyContext>(_ctx, getState());
  enterRule(_localctx, 8, CtkScriptParser::RuleBatchErrorPolicy);
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
    setState(215);
    _la = _input->LA(1);
    if (!(_la == CtkScriptParser::T__32

          || _la == CtkScriptParser::T__33)) {
      _errHandler->recoverInline(this);
    } else {
      _errHandler->reportMatch(this);
      consume();
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- ProgressPolicyContext
//------------------------------------------------------------------

CtkScriptParser::ProgressPolicyContext::ProgressPolicyContext(
    ParserRuleContext *parent, size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

size_t CtkScriptParser::ProgressPolicyContext::getRuleIndex() const {
  return CtkScriptParser::RuleProgressPolicy;
}

std::any CtkScriptParser::ProgressPolicyContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitProgressPolicy(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::ProgressPolicyContext *CtkScriptParser::progressPolicy() {
  ProgressPolicyContext *_localctx =
      _tracker.createInstance<ProgressPolicyContext>(_ctx, getState());
  enterRule(_localctx, 10, CtkScriptParser::RuleProgressPolicy);
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
    setState(217);
    _la = _input->LA(1);
    if (!(_la == CtkScriptParser::T__25

          || _la == CtkScriptParser::T__34)) {
      _errHandler->recoverInline(this);
    } else {
      _errHandler->reportMatch(this);
      consume();
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- MatcherExpressionContext
//------------------------------------------------------------------

CtkScriptParser::MatcherExpressionContext::MatcherExpressionContext(
    ParserRuleContext *parent, size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

std::vector<tree::TerminalNode *>
CtkScriptParser::MatcherExpressionContext::Identifier() {
  return getTokens(CtkScriptParser::Identifier);
}

tree::TerminalNode *
CtkScriptParser::MatcherExpressionContext::Identifier(size_t i) {
  return getToken(CtkScriptParser::Identifier, i);
}

std::vector<CtkScriptParser::MatcherArgumentsContext *>
CtkScriptParser::MatcherExpressionContext::matcherArguments() {
  return getRuleContexts<CtkScriptParser::MatcherArgumentsContext>();
}

CtkScriptParser::MatcherArgumentsContext *
CtkScriptParser::MatcherExpressionContext::matcherArguments(size_t i) {
  return getRuleContext<CtkScriptParser::MatcherArgumentsContext>(i);
}

size_t CtkScriptParser::MatcherExpressionContext::getRuleIndex() const {
  return CtkScriptParser::RuleMatcherExpression;
}

std::any CtkScriptParser::MatcherExpressionContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitMatcherExpression(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::MatcherExpressionContext *
CtkScriptParser::matcherExpression() {
  MatcherExpressionContext *_localctx =
      _tracker.createInstance<MatcherExpressionContext>(_ctx, getState());
  enterRule(_localctx, 12, CtkScriptParser::RuleMatcherExpression);
  size_t _la = 0;

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    size_t alt;
    enterOuterAlt(_localctx, 1);
    setState(219);
    match(CtkScriptParser::Identifier);
    setState(220);
    match(CtkScriptParser::T__18);
    setState(222);
    _errHandler->sync(this);

    _la = _input->LA(1);
    if ((((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 2130303778816) != 0)) {
      setState(221);
      matcherArguments();
    }
    setState(224);
    match(CtkScriptParser::T__19);
    setState(234);
    _errHandler->sync(this);
    alt = getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(_input, 24,
                                                                     _ctx);
    while (alt != 2 && alt != atn::ATN::INVALID_ALT_NUMBER) {
      if (alt == 1) {
        setState(225);
        match(CtkScriptParser::T__30);
        setState(226);
        match(CtkScriptParser::Identifier);
        setState(227);
        match(CtkScriptParser::T__18);
        setState(229);
        _errHandler->sync(this);

        _la = _input->LA(1);
        if ((((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 2130303778816) != 0)) {
          setState(228);
          matcherArguments();
        }
        setState(231);
        match(CtkScriptParser::T__19);
      }
      setState(236);
      _errHandler->sync(this);
      alt = getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(
          _input, 24, _ctx);
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- MatcherArgumentsContext
//------------------------------------------------------------------

CtkScriptParser::MatcherArgumentsContext::MatcherArgumentsContext(
    ParserRuleContext *parent, size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

std::vector<CtkScriptParser::MatcherArgumentContext *>
CtkScriptParser::MatcherArgumentsContext::matcherArgument() {
  return getRuleContexts<CtkScriptParser::MatcherArgumentContext>();
}

CtkScriptParser::MatcherArgumentContext *
CtkScriptParser::MatcherArgumentsContext::matcherArgument(size_t i) {
  return getRuleContext<CtkScriptParser::MatcherArgumentContext>(i);
}

size_t CtkScriptParser::MatcherArgumentsContext::getRuleIndex() const {
  return CtkScriptParser::RuleMatcherArguments;
}

std::any CtkScriptParser::MatcherArgumentsContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitMatcherArguments(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::MatcherArgumentsContext *CtkScriptParser::matcherArguments() {
  MatcherArgumentsContext *_localctx =
      _tracker.createInstance<MatcherArgumentsContext>(_ctx, getState());
  enterRule(_localctx, 14, CtkScriptParser::RuleMatcherArguments);
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
    setState(237);
    matcherArgument();
    setState(242);
    _errHandler->sync(this);
    _la = _input->LA(1);
    while (_la == CtkScriptParser::T__14) {
      setState(238);
      match(CtkScriptParser::T__14);
      setState(239);
      matcherArgument();
      setState(244);
      _errHandler->sync(this);
      _la = _input->LA(1);
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- MatcherArgumentContext
//------------------------------------------------------------------

CtkScriptParser::MatcherArgumentContext::MatcherArgumentContext(
    ParserRuleContext *parent, size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

CtkScriptParser::MatcherExpressionContext *
CtkScriptParser::MatcherArgumentContext::matcherExpression() {
  return getRuleContext<CtkScriptParser::MatcherExpressionContext>(0);
}

CtkScriptParser::ScalarContext *
CtkScriptParser::MatcherArgumentContext::scalar() {
  return getRuleContext<CtkScriptParser::ScalarContext>(0);
}

tree::TerminalNode *CtkScriptParser::MatcherArgumentContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

size_t CtkScriptParser::MatcherArgumentContext::getRuleIndex() const {
  return CtkScriptParser::RuleMatcherArgument;
}

std::any CtkScriptParser::MatcherArgumentContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitMatcherArgument(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::MatcherArgumentContext *CtkScriptParser::matcherArgument() {
  MatcherArgumentContext *_localctx =
      _tracker.createInstance<MatcherArgumentContext>(_ctx, getState());
  enterRule(_localctx, 16, CtkScriptParser::RuleMatcherArgument);

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    setState(248);
    _errHandler->sync(this);
    switch (getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(
        _input, 26, _ctx)) {
    case 1: {
      enterOuterAlt(_localctx, 1);
      setState(245);
      matcherExpression();
      break;
    }

    case 2: {
      enterOuterAlt(_localctx, 2);
      setState(246);
      scalar();
      break;
    }

    case 3: {
      enterOuterAlt(_localctx, 3);
      setState(247);
      match(CtkScriptParser::Identifier);
      break;
    }

    default:
      break;
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- ArgumentsContext
//------------------------------------------------------------------

CtkScriptParser::ArgumentsContext::ArgumentsContext(ParserRuleContext *parent,
                                                    size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

std::vector<CtkScriptParser::ArgumentContext *>
CtkScriptParser::ArgumentsContext::argument() {
  return getRuleContexts<CtkScriptParser::ArgumentContext>();
}

CtkScriptParser::ArgumentContext *
CtkScriptParser::ArgumentsContext::argument(size_t i) {
  return getRuleContext<CtkScriptParser::ArgumentContext>(i);
}

size_t CtkScriptParser::ArgumentsContext::getRuleIndex() const {
  return CtkScriptParser::RuleArguments;
}

std::any
CtkScriptParser::ArgumentsContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitArguments(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::ArgumentsContext *CtkScriptParser::arguments() {
  ArgumentsContext *_localctx =
      _tracker.createInstance<ArgumentsContext>(_ctx, getState());
  enterRule(_localctx, 18, CtkScriptParser::RuleArguments);
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
    setState(250);
    argument();
    setState(255);
    _errHandler->sync(this);
    _la = _input->LA(1);
    while (_la == CtkScriptParser::T__14) {
      setState(251);
      match(CtkScriptParser::T__14);
      setState(252);
      argument();
      setState(257);
      _errHandler->sync(this);
      _la = _input->LA(1);
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- ArgumentContext
//------------------------------------------------------------------

CtkScriptParser::ArgumentContext::ArgumentContext(ParserRuleContext *parent,
                                                  size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

size_t CtkScriptParser::ArgumentContext::getRuleIndex() const {
  return CtkScriptParser::RuleArgument;
}

void CtkScriptParser::ArgumentContext::copyFrom(ArgumentContext *ctx) {
  ParserRuleContext::copyFrom(ctx);
}

//----------------- PositionalArgumentContext
//------------------------------------------------------------------

CtkScriptParser::ExpressionContext *
CtkScriptParser::PositionalArgumentContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::PositionalArgumentContext::PositionalArgumentContext(
    ArgumentContext *ctx) {
  copyFrom(ctx);
}

std::any CtkScriptParser::PositionalArgumentContext::accept(
    tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitPositionalArgument(this);
  else
    return visitor->visitChildren(this);
}
//----------------- NamedArgumentContext
//------------------------------------------------------------------

tree::TerminalNode *CtkScriptParser::NamedArgumentContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

CtkScriptParser::ExpressionContext *
CtkScriptParser::NamedArgumentContext::expression() {
  return getRuleContext<CtkScriptParser::ExpressionContext>(0);
}

CtkScriptParser::NamedArgumentContext::NamedArgumentContext(
    ArgumentContext *ctx) {
  copyFrom(ctx);
}

std::any
CtkScriptParser::NamedArgumentContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitNamedArgument(this);
  else
    return visitor->visitChildren(this);
}
CtkScriptParser::ArgumentContext *CtkScriptParser::argument() {
  ArgumentContext *_localctx =
      _tracker.createInstance<ArgumentContext>(_ctx, getState());
  enterRule(_localctx, 20, CtkScriptParser::RuleArgument);

#if __cplusplus > 201703L
  auto onExit = finally([=, this] {
#else
  auto onExit = finally([=] {
#endif
    exitRule();
  });
  try {
    setState(262);
    _errHandler->sync(this);
    switch (getInterpreter<atn::ParserATNSimulator>()->adaptivePredict(
        _input, 28, _ctx)) {
    case 1: {
      _localctx =
          _tracker.createInstance<CtkScriptParser::NamedArgumentContext>(
              _localctx);
      enterOuterAlt(_localctx, 1);
      setState(258);
      match(CtkScriptParser::Identifier);
      setState(259);
      match(CtkScriptParser::T__1);
      setState(260);
      expression(0);
      break;
    }

    case 2: {
      _localctx =
          _tracker.createInstance<CtkScriptParser::PositionalArgumentContext>(
              _localctx);
      enterOuterAlt(_localctx, 2);
      setState(261);
      expression(0);
      break;
    }

    default:
      break;
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- ScalarContext
//------------------------------------------------------------------

CtkScriptParser::ScalarContext::ScalarContext(ParserRuleContext *parent,
                                              size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

tree::TerminalNode *CtkScriptParser::ScalarContext::StringLiteral() {
  return getToken(CtkScriptParser::StringLiteral, 0);
}

tree::TerminalNode *CtkScriptParser::ScalarContext::Number() {
  return getToken(CtkScriptParser::Number, 0);
}

size_t CtkScriptParser::ScalarContext::getRuleIndex() const {
  return CtkScriptParser::RuleScalar;
}

std::any
CtkScriptParser::ScalarContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitScalar(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::ScalarContext *CtkScriptParser::scalar() {
  ScalarContext *_localctx =
      _tracker.createInstance<ScalarContext>(_ctx, getState());
  enterRule(_localctx, 22, CtkScriptParser::RuleScalar);
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
    setState(264);
    _la = _input->LA(1);
    if (!((((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 1855425871872) != 0))) {
      _errHandler->recoverInline(this);
    } else {
      _errHandler->reportMatch(this);
      consume();
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- MemberNameContext
//------------------------------------------------------------------

CtkScriptParser::MemberNameContext::MemberNameContext(ParserRuleContext *parent,
                                                      size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

tree::TerminalNode *CtkScriptParser::MemberNameContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

size_t CtkScriptParser::MemberNameContext::getRuleIndex() const {
  return CtkScriptParser::RuleMemberName;
}

std::any
CtkScriptParser::MemberNameContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitMemberName(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::MemberNameContext *CtkScriptParser::memberName() {
  MemberNameContext *_localctx =
      _tracker.createInstance<MemberNameContext>(_ctx, getState());
  enterRule(_localctx, 24, CtkScriptParser::RuleMemberName);
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
    setState(266);
    _la = _input->LA(1);
    if (!((((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 283476230144) != 0))) {
      _errHandler->recoverInline(this);
    } else {
      _errHandler->reportMatch(this);
      consume();
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

//----------------- ObjectKeyContext
//------------------------------------------------------------------

CtkScriptParser::ObjectKeyContext::ObjectKeyContext(ParserRuleContext *parent,
                                                    size_t invokingState)
    : ParserRuleContext(parent, invokingState) {}

tree::TerminalNode *CtkScriptParser::ObjectKeyContext::Identifier() {
  return getToken(CtkScriptParser::Identifier, 0);
}

tree::TerminalNode *CtkScriptParser::ObjectKeyContext::StringLiteral() {
  return getToken(CtkScriptParser::StringLiteral, 0);
}

size_t CtkScriptParser::ObjectKeyContext::getRuleIndex() const {
  return CtkScriptParser::RuleObjectKey;
}

std::any
CtkScriptParser::ObjectKeyContext::accept(tree::ParseTreeVisitor *visitor) {
  if (auto parserVisitor = dynamic_cast<CtkScriptVisitor *>(visitor))
    return parserVisitor->visitObjectKey(this);
  else
    return visitor->visitChildren(this);
}

CtkScriptParser::ObjectKeyContext *CtkScriptParser::objectKey() {
  ObjectKeyContext *_localctx =
      _tracker.createInstance<ObjectKeyContext>(_ctx, getState());
  enterRule(_localctx, 26, CtkScriptParser::RuleObjectKey);
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
    setState(268);
    _la = _input->LA(1);
    if (!((((_la & ~0x3fULL) == 0) && ((1ULL << _la) & 833232044032) != 0))) {
      _errHandler->recoverInline(this);
    } else {
      _errHandler->reportMatch(this);
      consume();
    }

  } catch (RecognitionException &e) {
    _errHandler->reportError(this, e);
    _localctx->exception = std::current_exception();
    _errHandler->recover(this, _localctx->exception);
  }

  return _localctx;
}

bool CtkScriptParser::sempred(RuleContext *context, size_t ruleIndex,
                              size_t predicateIndex) {
  switch (ruleIndex) {
  case 2:
    return expressionSempred(antlrcpp::downCast<ExpressionContext *>(context),
                             predicateIndex);

  default:
    break;
  }
  return true;
}

bool CtkScriptParser::expressionSempred(ExpressionContext *_localctx,
                                        size_t predicateIndex) {
  switch (predicateIndex) {
  case 0:
    return precpred(_ctx, 3);
  case 1:
    return precpred(_ctx, 2);

  default:
    break;
  }
  return true;
}

void CtkScriptParser::initialize() {
#if ANTLR4_USE_THREAD_LOCAL_CACHE
  ctkscriptParserInitialize();
#else
  ::antlr4::internal::call_once(ctkscriptParserOnceFlag,
                                ctkscriptParserInitialize);
#endif
}
