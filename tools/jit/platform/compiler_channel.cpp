#include "compiler_channel.hpp"

#include <cstdlib>

#include <llvm/Support/JSON.h>

namespace ctk::jit {

CompilerChannel::CompilerChannel(bool enabled) {
  if (!enabled)
    return;
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
  if (!input)
    return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                   "dynamic CTK compilation requires the ctk-jit frontend");
  return request(llvm::json::Object{{"source", source}, {"path", path}, {"library", library}}, "ir");
}

std::optional<std::string> CompilerChannel::render(llvm::StringRef kind, llvm::json::Value value) {
  if (!input)
    return std::nullopt;
  auto result = request(llvm::json::Object{{"render", kind}, {"value", std::move(value)}}, "text");
  if (result)
    return std::move(*result);
  llvm::consumeError(result.takeError());
  return std::nullopt;
}

llvm::Error CompilerChannel::history(llvm::StringRef action, const std::string* value) {
  if (!input && action == "label")
    return llvm::Error::success();
  if (!input)
    return llvm::createStringError(llvm::inconvertibleErrorCode(), "history is not enabled");
  auto reply = request(llvm::json::Object{{"history", action}, {"value", value ? llvm::json::Value(*value)
                                                          : llvm::json::Value(nullptr)}}, "status");
  return reply ? llvm::Error::success() : reply.takeError();
}

llvm::Expected<std::string> CompilerChannel::request(llvm::json::Object body,
                                                     llvm::StringRef result) {
  auto error = [](const llvm::Twine& message) {
    return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
  };
  llvm::raw_fd_ostream output(fd, false);
  output << llvm::json::Value(std::move(body)) << '\n';
  output.flush();
  if (output.has_error()) {
    output.clear_error();
    return error("could not write to the CTK frontend");
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
    if (const auto value = object->getString(result))
      return value->str();
    if (const auto diagnostic = object->getString("error"))
      return error(*diagnostic);
  }
  return error("invalid CTK frontend response");
}

} // namespace ctk::jit
