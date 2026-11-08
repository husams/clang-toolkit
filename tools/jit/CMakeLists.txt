cmake_minimum_required(VERSION 3.24)
include(../../cmake/Platform.cmake)
project(ctk_jit LANGUAGES C CXX)

find_package(LLVM REQUIRED CONFIG)
find_package(Clang REQUIRED CONFIG)
if(APPLE AND NOT DEFINED ICU_ROOT)
  foreach(prefix /opt/homebrew/opt/icu4c /usr/local/opt/icu4c)
    if(IS_DIRECTORY "${prefix}/include/unicode")
      set(ICU_ROOT "${prefix}")
      break()
    endif()
  endforeach()
endif()
find_package(ICU REQUIRED COMPONENTS uc data)
find_path(CTK_JIT_YAML_INCLUDE_DIR yaml.h REQUIRED)
find_library(CTK_JIT_YAML_LIBRARY yaml REQUIRED)
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

add_executable(ctk-jit-runner main.cpp ir.cpp values.cpp filters.cpp documents.cpp platform/compiler_channel.cpp
  ../../server/src/clang/matcher_parser.cpp ../../server/src/clang/scoped_match.cpp)
target_compile_features(ctk-jit-runner PRIVATE cxx_std_20)
set_target_properties(ctk-jit-runner PROPERTIES CXX_EXTENSIONS OFF)
target_include_directories(ctk-jit-runner PRIVATE include ../../server/src/clang "${CTK_JIT_YAML_INCLUDE_DIR}")
target_include_directories(ctk-jit-runner SYSTEM PRIVATE ${CLANG_INCLUDE_DIRS} ${LLVM_INCLUDE_DIRS})
target_compile_definitions(ctk-jit-runner PRIVATE
  CTK_JIT_COMPILER="${CTK_JIT_CLANG}"
  CTK_JIT_CLANG_LIBRARY="$<TARGET_FILE:clang-cpp>"
  CTK_JIT_LLVM_LIBRARY="$<TARGET_FILE:LLVM>"
  CTK_JIT_ICU_LIBRARY="$<TARGET_FILE:ICU::uc>"
  CTK_JIT_ICU_DATA="$<TARGET_FILE:ICU::data>"
  CTK_JIT_YAML_LIBRARY="${CTK_JIT_YAML_LIBRARY}"
  CTK_JIT_PRELUDE="${CMAKE_CURRENT_SOURCE_DIR}/prelude.hpp"
  CTK_JIT_SDK_INCLUDE="${CMAKE_CURRENT_SOURCE_DIR}/include"
  CTK_JIT_CLANG_INCLUDE="${CLANG_INCLUDE_DIRS}"
  CTK_JIT_LLVM_INCLUDE="${LLVM_INCLUDE_DIRS}"
  CTK_JIT_RESOURCE_DIR="${CTK_JIT_RESOURCE_DIR}"
  CTK_JIT_SYSROOT="${CTK_JIT_SYSROOT}")
target_link_libraries(ctk-jit-runner PRIVATE clang-cpp LLVM ICU::uc "${CTK_JIT_YAML_LIBRARY}")
