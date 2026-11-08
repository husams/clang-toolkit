#include "compiler_channel.hpp"

#include <cstdlib>

#include <llvm/Support/JSON.h>

namespace ctk::jit {

CompilerChannel::CompilerChannel() {
  if (const auto* value = std::getenv("CTK_JIT_COMPILER_FD")) {
    unsigned descriptor;
    if (!llvm::StringRef(value).getAsInteger(10, descriptor) && descriptor >= 3) {
      fd = descriptor;
      input.reset(::fdopen(fd, "r"));
    }
  }
}

llvm::Expected<std::string> CompilerChannel::lower(llvm::StringRef source, llvm::StringRef path,
                                                   bool library) {
  auto error = [](const llvm::Twine& message) {
    return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
  };
  if (!input)
    return error("dynamic CTK compilation requires the ctk-jit frontend");
  llvm::raw_fd_ostream output(fd, false);
  output << llvm::json::Value(llvm::json::Object{
                {"source", source},
                {"path", path},
                {"library", library},
            })
         << '\n';
  output.flush();
  if (output.has_error()) {
    output.clear_error();
    return error("could not request CTK compilation");
  }

  char* line = nullptr;
  std::size_t capacity = 0;
  const auto size = ::getline(&line, &capacity, input.get());
  std::unique_ptr<char, decltype(&std::free)> contents(line, &std::free);
  if (size < 0)
    return error("CTK compiler channel closed");
  auto reply = llvm::json::parse(llvm::StringRef(line, size));
  if (!reply)
    return reply.takeError();
  const auto* object = reply->getAsObject();
  if (object) {
    if (const auto ir = object->getString("ir"))
      return ir->str();
    if (const auto diagnostic = object->getString("error"))
      return error(*diagnostic);
  }
  return error("invalid CTK compilation response");
}

} // namespace ctk::jit
