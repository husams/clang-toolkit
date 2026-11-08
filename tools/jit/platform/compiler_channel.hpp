#pragma once

#include <cstdio>
#include <memory>
#include <string>

#include <llvm/ADT/StringRef.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/JSON.h>

namespace ctk::jit {

class CompilerChannel {
public:
  CompilerChannel();
  llvm::Expected<std::string> lower(llvm::StringRef source, llvm::StringRef path, bool library);

  llvm::Error history(llvm::StringRef action, const std::string* value);

private:
  llvm::Expected<std::string> request(llvm::json::Object body, llvm::StringRef result);

  int fd = -1;
  std::unique_ptr<std::FILE, decltype(&std::fclose)> input{nullptr, &std::fclose};
};

} // namespace ctk::jit
