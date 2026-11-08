#pragma once

#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <llvm/Support/raw_ostream.h>

namespace ctk::jit {

class RunContext {
public:
  explicit RunContext(clang::ASTContext &ast) : ast_(ast) {}

  template <class Matcher, class Callback>
  void match(const Matcher &matcher, Callback callback) {
    using Finder = clang::ast_matchers::MatchFinder;
    struct Handler final : Finder::MatchCallback {
      explicit Handler(Callback &callback) : callback_(callback) {}

      void run(const Finder::MatchResult &result) override {
        callback_(result);
      }

      Callback &callback_;
    };
    Handler handler(callback);
    Finder finder;
    finder.addMatcher(matcher, &handler);
    finder.matchAST(ast_);
  }

  void emit_text(llvm::StringRef text) { llvm::outs() << text << '\n'; }

private:
  clang::ASTContext &ast_;
};

} // namespace ctk::jit
