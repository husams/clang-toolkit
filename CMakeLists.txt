cmake_minimum_required(VERSION 3.24)

# Platform toolchain discovery (macOS: Homebrew LLVM; RHEL: system clang/clang-devel).
include(cmake/Platform.cmake)
project(clang_toolkit LANGUAGES C CXX VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(CTK_WITH_CLANG "Build the Clang API layer (requires LLVM/Clang dev libs)" ON)
option(CTK_BUILD_TESTS "Build C++ unit tests" ON)

add_subdirectory(server)

if(CTK_BUILD_TESTS)
  enable_testing()
  add_subdirectory(server/tests)
endif()
