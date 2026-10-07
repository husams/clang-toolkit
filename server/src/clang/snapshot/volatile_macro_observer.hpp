#pragma once
#include <clang/Lex/MacroInfo.h>
#include <clang/Lex/PPCallbacks.h>
namespace ctk::clang_layer::snapshot {
class VolatileMacroObserver final : public clang::PPCallbacks {
public:
  explicit VolatileMacroObserver(bool &observed) : observed_(observed) {}
  void MacroExpands(const clang::Token &token,
                    const clang::MacroDefinition &definition,
                    clang::SourceRange, const clang::MacroArgs *) override {
    const auto *macro = definition.getMacroInfo();
    const auto *identifier = token.getIdentifierInfo();
    if (!macro || !macro->isBuiltinMacro() || !identifier)
      return;
    const auto name = identifier->getName();
    if (name == "__DATE__" || name == "__TIME__" || name == "__TIMESTAMP__")
      observed_ = true;
  }

private:
  bool &observed_;
};
} // namespace ctk::clang_layer::snapshot
