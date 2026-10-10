// Enumerate matchers reachable through Clang's public dynamic completion API.
// The Python driver records the output as an offline console completion catalog.
#include "clang/ASTMatchers/Dynamic/Registry.h"
#include "llvm/ADT/StringRef.h"

#include <iostream>
#include <set>
#include <string>
#include <utility>
#include <vector>

using namespace clang::ast_matchers::dynamic;

static std::string matcherName(const MatcherCompletion &Completion) {
  llvm::StringRef Text(Completion.TypedText);
  return Text.take_front(Text.find('(')).str();
}

int main() {
  std::set<std::string> Names;
  std::set<std::string> Roots;
  auto AddCompletions = [&](const std::vector<ArgKind> &Types,
                            bool RootContext) {
    for (const MatcherCompletion &Completion :
         Registry::getMatcherCompletions(Types)) {
      std::string Name = matcherName(Completion);
      auto Ctor = Registry::lookupMatcherCtor(Name);
      if (!Ctor)
        continue;
      Names.insert(Name);
      if (RootContext && !Registry::nodeMatcherType(*Ctor).isNone())
        Roots.insert(Name);
    }
  };

  AddCompletions(Registry::getAcceptedCompletionTypes({}), true);
  bool Changed = true;
  while (Changed) {
    Changed = false;
    std::vector<std::string> Current(Names.begin(), Names.end());
    for (const std::string &Name : Current) {
      auto Ctor = Registry::lookupMatcherCtor(Name);
      if (!Ctor)
        continue;
      for (unsigned Argument = 0; Argument < 8; ++Argument) {
        const auto Types = Registry::getAcceptedCompletionTypes(
            {{*Ctor, Argument}});
        const std::size_t Before = Names.size();
        AddCompletions(Types, false);
        Changed |= Names.size() != Before;
      }
    }
  }

  for (const std::string &Name : Names)
    std::cout << Name << '\t' << (Roots.count(Name) ? '1' : '0') << '\n';
}
