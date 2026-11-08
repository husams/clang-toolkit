#pragma once

#include <filesystem>
#include <optional>
#include <string>

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/JSON.h>

namespace ctk::jit {

class NativeHistory {
public:
  NativeHistory();

  llvm::Expected<llvm::json::Array> read() const;
  llvm::Error append(llvm::StringRef command) const;
  llvm::Error action(llvm::StringRef name, const std::string *text);
  bool take_cleared();

private:
  std::filesystem::path path;
  std::string session;
  std::optional<std::string> label;
  bool cleared = false;
};

} // namespace ctk::jit
