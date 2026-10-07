#pragma once
#include "native_ast_writer.hpp"
#include <clang/AST/ASTConsumer.h>
namespace ctk::clang_layer::snapshot {
class SerializationObserver final : public clang::ASTConsumer {
public:
  explicit SerializationObserver(NativeAstWriter &writer) : writer_(writer) {}
  clang::ASTMutationListener *GetASTMutationListener() override {
    return &writer_.writer();
  }
  clang::ASTDeserializationListener *GetASTDeserializationListener() override {
    return &writer_.writer();
  }

private:
  NativeAstWriter &writer_;
};
} // namespace ctk::clang_layer::snapshot
