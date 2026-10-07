#pragma once
#include "native_ast_writer.hpp"
#include <clang/Frontend/ASTUnit.h>
#include <llvm/Support/VirtualFileSystem.h>
namespace ctk::clang_layer::snapshot {
std::unique_ptr<clang::ASTUnit>
build_snapshot(const std::string &path,
               const std::vector<std::string> &arguments,
               const std::string &tool,
               llvm::IntrusiveRefCntPtr<llvm::vfs::FileSystem> filesystem,
               bool &volatile_input, std::unique_ptr<NativeAstWriter> &writer);
}
