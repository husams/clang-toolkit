cmake_minimum_required(VERSION 3.24)
include(../../cmake/Platform.cmake)
project(ctk_jit LANGUAGES C CXX)

find_package(LLVM REQUIRED CONFIG)
find_package(Clang REQUIRED CONFIG)
if(LLVM_PACKAGE_VERSION VERSION_LESS 21 OR NOT TARGET clang-cpp OR NOT TARGET LLVM)
  message(FATAL_ERROR "ctk-jit requires LLVM 21 or newer with shared Clang and LLVM libraries")
endif()

find_program(CTK_JIT_CLANG clang++ HINTS "${LLVM_TOOLS_BINARY_DIR}" NO_DEFAULT_PATH REQUIRED)
execute_process(COMMAND "${CTK_JIT_CLANG}" -print-resource-dir
  OUTPUT_VARIABLE CTK_JIT_RESOURCE_DIR OUTPUT_STRIP_TRAILING_WHITESPACE
  COMMAND_ERROR_IS_FATAL ANY)

set(CTK_JIT_SYSROOT "")
if(APPLE)
  if(IS_DIRECTORY "${CMAKE_OSX_SYSROOT}")
    set(CTK_JIT_SYSROOT "${CMAKE_OSX_SYSROOT}")
  else()
    execute_process(COMMAND xcrun --sdk macosx --show-sdk-path
      OUTPUT_VARIABLE CTK_JIT_SYSROOT OUTPUT_STRIP_TRAILING_WHITESPACE
      COMMAND_ERROR_IS_FATAL ANY)
  endif()
endif()

add_executable(ctk-jit-runner main.cpp)
target_compile_features(ctk-jit-runner PRIVATE cxx_std_20)
set_target_properties(ctk-jit-runner PROPERTIES CXX_EXTENSIONS OFF)
target_include_directories(ctk-jit-runner PRIVATE include)
target_include_directories(ctk-jit-runner SYSTEM PRIVATE ${CLANG_INCLUDE_DIRS} ${LLVM_INCLUDE_DIRS})
target_compile_definitions(ctk-jit-runner PRIVATE
  CTK_JIT_SDK_INCLUDE="${CMAKE_CURRENT_SOURCE_DIR}/include"
  CTK_JIT_CLANG_INCLUDE="${CLANG_INCLUDE_DIRS}"
  CTK_JIT_LLVM_INCLUDE="${LLVM_INCLUDE_DIRS}"
  CTK_JIT_RESOURCE_DIR="${CTK_JIT_RESOURCE_DIR}"
  CTK_JIT_SYSROOT="${CTK_JIT_SYSROOT}")
target_link_libraries(ctk-jit-runner PRIVATE clang-cpp LLVM)
